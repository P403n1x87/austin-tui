# This file is part of "austin-tui" which is released under GPL.
#
# See file LICENCE or go to http://www.gnu.org/licenses/ for full license
# details.
#
# austin-tui is top-like TUI for Austin.
#
# Copyright (c) 2018-2021 Gabriele N. Tornetta <phoenix1987@gmail.com>.
# All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from typing import Any
from typing import Optional
from typing import Union

from austin.stats import ThreadStats

from austin_tui import AustinProfileMode
from austin_tui.model import Model
from austin_tui.model.austin import AustinModel
from austin_tui.model.system import Bytes
from austin_tui.model.system import FrozenSystemModel
from austin_tui.model.system import Percentage
from austin_tui.model.system import SystemModel
from austin_tui.view import View
from austin_tui.widgets.graph import FlameGraphData
from austin_tui.widgets.markup import AttrString
from austin_tui.widgets.markup import escape
from austin_tui.widgets.table import TableData


class Adapter:
    """Model-View adapter.

    Bridges between a data model and the actual data structure required by a
    widget so that it can be displayed in a view.

    An adapter is made of two steps: ``transform`` and ``update``. The former
    transforms the model data into a format that is suitable for representation
    for the given widget. The latter is responsible for updating the widget
    appearance.

    An adapter is used by simply calling it.
    """

    def __init__(self, model: Model, view: View) -> None:
        self._model = model
        self._view = view

    def __call__(self) -> bool:
        """Invoke the adapter."""
        return self.update(self.transform())

    def transform(self) -> Any:
        """Transform the model data into the widget data."""
        pass

    def update(self, data: Any) -> bool:
        """Update the view with the widget data."""
        pass


class FreezableAdapter(Adapter):
    """An adapter with freezable widget data."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._frozen = False
        self._data: Optional[Any] = None

    def __call__(self) -> bool:
        """Invoke the adapter on either live or frozen data."""
        if self._frozen:
            return self.update(self.defrost())
        return super().__call__()

    def freeze(self) -> None:
        """Freeze the widget data."""
        self._data = self.transform()
        self._frozen = True

    def defrost(self) -> Any:
        """Retrieve the frozen data.

        Implement to return the frozen data.
        """
        return self._data

    def unfreeze(self) -> None:
        """Unfreeze the adapter."""
        self._frozen = False

    @property
    def frozen(self) -> bool:
        """The freeze status of the adapter."""
        return self._frozen


class CommandLineAdapter(FreezableAdapter):
    """Command line adapter."""

    def transform(self) -> AttrString:
        """Retrieve the command line."""
        cmd = self._model.austin.command_line
        exec, _, args = cmd.partition(" ")
        return self._view.markup(f"<exec><b>{escape(exec)}</b></exec> {escape(args)}")

    def update(self, data: AttrString) -> bool:
        """Update the widget."""
        return self._view.cmd_line.set_text(data)


class CountAdapter(FreezableAdapter):
    """Sample count adapter."""

    def transform(self) -> int:
        """Retrieve the count."""
        return self._model.austin.samples_count

    def update(self, data: int) -> bool:
        """Update the widget."""
        return self._view.samples.set_text(data)


class CpuAdapter(Adapter):
    """CPU metrics adapter."""

    def transform(self) -> Percentage:
        """Get the CPU usage."""
        return self._model.system.get_cpu(self._model.system.child_process)

    def update(self, data: Percentage) -> bool:
        """Update the metric and the plot."""
        self._view.cpu.set_text(f"{data}% ")
        self._view.cpu_plot.push(data)
        return True


class MemoryAdapter(Adapter):
    """Memory usage adapter."""

    def transform(self) -> Bytes:
        """Get memory usage."""
        return self._model.system.get_memory(self._model.system.child_process)

    def update(self, data: Bytes) -> bool:
        """Update metric and plot."""
        self._view.mem.set_text(f"{data>>20}M ")
        self._view.mem_plot.push(data)
        return True


def fmt_time(s: int) -> str:
    """Format microseconds into mm':ss''."""
    m = int(s // 60e6)
    ret = '{:02d}"'.format(round(s / 1e6) % 60)
    if m:
        ret = str(m) + "'" + ret

    return ret


class DurationAdapter(FreezableAdapter):
    """Duration adapter."""

    def transform(self) -> str:
        """Get duration."""
        return fmt_time(int(self._model.system.duration * 1e6))

    def update(self, data: str) -> bool:
        """Update the widget."""
        return self._view.duration.set_text(data)


class CurrentThreadAdapter(Adapter):
    """Currently selected thread adapter."""

    def transform(self) -> Union[str, AttrString]:
        """Get current thread."""
        austin = self._model.frozen_austin if self._model.frozen else self._model.austin
        n = len(austin.threads)
        if not n:
            return "--/--"

        return self._view.markup(
            f"<thread>{austin.current_thread + 1}</thread><hdrbox>/{n}</hdrbox>"
        )

    def update(self, data: Union[str, AttrString]) -> bool:
        """Update the widget."""
        return self._view.thread_num.set_text(data)


class ThreadNameAdapter(FreezableAdapter):
    """Currently selected thread name adapter."""

    def transform(self) -> Union[str, AttrString]:
        """Get the thread name."""
        austin = self._model.frozen_austin if self._model.frozen else self._model.austin
        if austin.threads:
            pid, _, tid = austin.threads[austin.current_thread].partition(":")
            return self._view.markup(f"<pid><b>{pid}</b></pid>:<tid><b>{tid}</b></tid>")
        return "--:--"

    def update(self, data: Union[str, AttrString]) -> bool:
        """Update the widget."""
        return self._view.thread_name.set_text(data)


class BaseThreadDataAdapter(Adapter):
    """Base implementation for the thread table data adapter."""

    def transform(self) -> TableData:
        """Transform according to the right model."""
        austin = self._model.frozen_austin if self._model.frozen else self._model.austin
        system = self._model.frozen_system if self._model.frozen else self._model.system
        return self._transform(austin, system)

    def update(self, data: TableData) -> bool:
        """Update the table."""
        return self._view.table.set_data(data)


class ThreadDataAdapter(BaseThreadDataAdapter):
    """Thread table data adapter."""

    def _transform(
        self, austin: AustinModel, system: Union[SystemModel, FrozenSystemModel]
    ) -> TableData:
        formatter, scaler = (
            (self._view.fmt_mem, self._view.scale_memory)
            if self._view.mode == AustinProfileMode.MEMORY
            else (self._view.fmt_time, self._view.scale_time)
        )
        thread_key = austin.threads[austin.current_thread]
        pid, _, thread = thread_key.partition(":")

        thread_stats = austin.stats.processes[int(pid)].threads[thread]
        frames = austin.get_last_stack(thread_key).frames

        container = thread_stats.children
        frame_stats = []
        max_scale = (
            system.max_memory
            if self._view.mode == AustinProfileMode.MEMORY
            else system.duration
        )
        for frame in frames:
            child_frame_stats = container[frame]
            if (
                child_frame_stats.total.value / 1e6 / max_scale
                < self._model.austin.threshold
            ):
                break
            frame_stats.append(
                [
                    formatter(child_frame_stats.own.value),
                    formatter(child_frame_stats.total.value),
                    scaler(child_frame_stats.own.value, max_scale),
                    scaler(child_frame_stats.total.value, max_scale),
                    self._view.markup(
                        " "
                        + escape(child_frame_stats.label.function)
                        + f" <inactive>({escape(child_frame_stats.label.filename)}"
                        f":{child_frame_stats.label.line})</inactive>"
                    ),
                ]
            )
            container = child_frame_stats.children

        return frame_stats


class ThreadFullDataAdapter(BaseThreadDataAdapter):
    """Full thread data adapter."""

    def _transform(
        self, austin: AustinModel, system: Union[SystemModel, FrozenSystemModel]
    ) -> TableData:
        formatter, scaler = (
            (self._view.fmt_mem, self._view.scale_memory)
            if self._view.mode == AustinProfileMode.MEMORY
            else (self._view.fmt_time, self._view.scale_time)
        )

        thread_key = austin.threads[austin.current_thread]
        pid, _, thread = thread_key.partition(":")

        frames = austin.get_last_stack(thread_key).frames
        frame_stats = []
        max_scale = (
            system.max_memory
            if self._view.mode == AustinProfileMode.MEMORY
            else system.duration
        )

        def _add_frame_stats(
            stats: ThreadStats,
            marker: str,
            prefix: str,
            level: int = 0,
            active_bucket: Optional[dict] = None,
            active_parent: bool = True,
        ) -> None:
            if stats.total.value / 1e6 / max_scale < self._model.austin.threshold:
                return
            try:
                active = (
                    active_bucket is not None
                    and stats.label in active_bucket
                    and stats.label == frames[level]
                    and active_parent
                )
                active_bucket = stats.children
            except IndexError:
                active = False
                active_bucket = None

            frame_stats.append(
                [
                    formatter(stats.own.value, active),
                    formatter(stats.total.value, active),
                    scaler(stats.own.value, max_scale, active),
                    scaler(stats.total.value, max_scale, active),
                    self._view.markup(
                        " "
                        + f"<inactive>{marker}</inactive>"
                        + (
                            escape(stats.label.function)
                            if active
                            else f"<inactive>{escape(stats.label.function)}</inactive>"
                        )
                        + f" <inactive>(<filename>{escape(stats.label.filename)}</filename>"
                        f":<lineno>{stats.label.line}</lineno>)</inactive>"
                    ),
                ]
            )
            children_stats = [child_stats for _, child_stats in stats.children.items()]
            if not children_stats:
                return
            for child_stats in children_stats[:-1]:
                _add_frame_stats(
                    child_stats,
                    prefix + "├─ ",
                    prefix + "│  ",
                    level + 1,
                    active_bucket,
                    active,
                )

            _add_frame_stats(
                children_stats[-1],
                prefix + "└─ ",
                prefix + "   ",
                level + 1,
                active_bucket,
                active,
            )

        thread_stats = austin.stats.processes[int(pid)].threads[thread]

        children = [stats for _, stats in thread_stats.children.items()]
        if children:
            for stats in children[:-1]:
                _add_frame_stats(stats, "├─ ", "│  ", 0, thread_stats.children)

            _add_frame_stats(children[-1], "└─ ", "   ", 0, thread_stats.children)

        return frame_stats


class FlameGraphAdapter(Adapter):
    """Flame graph data adapter."""

    def transform(self) -> dict:
        """Transform according to the right model."""
        austin = self._model.frozen_austin if self._model.frozen else self._model.austin
        system = self._model.frozen_system if self._model.frozen else self._model.system
        return self._transform(austin, system)  # type: ignore[arg-type]

    def _transform(
        self, austin: AustinModel, system: Union[SystemModel, FrozenSystemModel]
    ) -> dict:
        thread_key = austin.threads[austin.current_thread]
        pid, _, thread = thread_key.partition(":")

        thread = austin.stats.processes[int(pid)].threads[thread]

        cs = {}  # type: ignore[var-annotated]
        total = thread.total.value
        total_pct = min(int(total / system.duration / 1e4), 100)
        data: FlameGraphData = {
            f"THREAD {thread.label} ⏲️  {fmt_time(total)} ({total_pct}%)": (total, cs)
        }
        levels = [(c, cs) for c in thread.children.values()]
        while levels:
            level, c = levels.pop(0)
            k = f"{level.label.function} ({level.label.filename})"
            if k in c:
                v, cs = c[k]
                c[k] = (v + level.total.value, cs)
            else:
                cs = {}
                c[k] = (level.total.value, cs)
            levels.extend(((c, cs) for c in level.children.values()))

        return data

    def update(self, data: FlameGraphData) -> bool:
        """Update the table."""
        (header,) = data
        return self._view.flamegraph.set_data(data) | self._view.graph_header.set_text(
            " FLAME GRAPH FOR " + header
        )
