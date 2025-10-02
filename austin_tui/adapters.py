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
from typing import Set
from typing import Union

from austin.events import ThreadName
from austin.stats import HierarchicalStats

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
        exec, *args = cmd
        return self._view.markup(
            f"<exec><b>{escape(exec)}</b></exec> {escape(' '.join(args))}"
        )

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
        self._view.mem.set_text(f"{data >> 20}M ")
        self._view.mem_plot.push(data)
        return True


def fmt_time(us: int) -> str:
    """Format microseconds into [mm]m[ss[.ff]]s."""
    s = us / 1e6
    m = int(s // 60)
    return f"{m:02d}m{s:02d}s" if m else f"{s:.2f}s"


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

        pid, _, thread_name = thread_key.partition(":")
        iid, _, thread = thread_name.partition(":")
        thread_stats = austin.stats.processes[int(pid)].threads[
            ThreadName(thread, int(iid))
        ]
        frames = austin.get_last_stack(thread_key).frames

        container = thread_stats.children
        frame_stats = []
        max_scale = (
            system.max_memory
            if self._view.mode == AustinProfileMode.MEMORY
            else system.duration
        )

        for frame in frames or []:
            child_frame_stats = container[frame]
            if child_frame_stats.total / 1e6 / max_scale < self._model.austin.threshold:
                break
            column = (
                f":<lineno>{child_frame_stats.label.column}</lineno>"
                if child_frame_stats.label.column
                else ""
            )
            location = self._view.markup(
                " "
                + escape(child_frame_stats.label.function)
                + f" <inactive>(<filename>{escape(child_frame_stats.label.filename)}</filename>"
                f":<lineno>{child_frame_stats.label.line}</lineno>{column})</inactive>"
            )
            frame_stats.append(
                [
                    formatter(child_frame_stats.own),
                    formatter(child_frame_stats.total),
                    scaler(child_frame_stats.own, max_scale),
                    scaler(child_frame_stats.total, max_scale),
                    location,
                ]
            )
            container = child_frame_stats.children

        return frame_stats


class ThreadTopDataAdapter(BaseThreadDataAdapter):
    """Thread table top data adapter."""

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

        frame_stats = {}
        max_scale = (
            system.max_memory
            if self._view.mode == AustinProfileMode.MEMORY
            else system.duration
        )

        def _add_frame_stats(
            stats: HierarchicalStats, seen_locations: Set[str]
        ) -> None:
            if len(frame_stats) == MAX_LENGTH:
                frame_stats.append(
                    [
                        " " * 8,
                        " " * 8,
                        " " * 8,
                        " " * 8,
                        self._view.markup(
                            " <inactive>[truncated view; export the data to MOJO to see more with other tools]</inactive>"
                        ),
                    ]
                )
                return
            if len(frame_stats) > MAX_LENGTH:
                return
            if stats.total / 1e6 / max_scale < self._model.austin.threshold:
                return

            column = (
                f":<lineno>{stats.label.column}</lineno>" if stats.label.column else ""
            )
            location = (
                (escape(stats.label.function))
                + f" <inactive>(<filename>{escape(stats.label.filename)}</filename>:<lineno>{stats.label.line}</lineno>{column})</inactive>"
            )
            frame_stats[location] = (
                frame_stats.get(location, 0)
                + stats.own
                + 1j * stats.total * (location not in seen_locations)
            )

            if not (children_stats := list(stats.children.values())):
                return

            new_seen_locations = seen_locations | {location}
            for child_stats in children_stats[:-1]:
                _add_frame_stats(child_stats, new_seen_locations)

            _add_frame_stats(children_stats[-1], new_seen_locations)

        pid, _, thread_name = thread_key.partition(":")
        iid, _, thread = thread_name.partition(":")
        thread_stats = austin.stats.processes[int(pid)].threads[
            ThreadName(thread, int(iid))
        ]
        if children := list(thread_stats.children.values()):
            for stats in children[:-1]:
                _add_frame_stats(stats, set())

            _add_frame_stats(children[-1], set())

        return [
            (
                formatter(int(m.real), True),
                formatter(int(m.imag), True),
                scaler(int(m.real), max_scale, True),
                scaler(int(m.imag), max_scale, True),
                self._view.markup(location),
            )
            for location, m in sorted(
                frame_stats.items(), reverse=True, key=lambda _: _[1].real
            )
        ]


MAX_DEPTH = 64
MAX_LENGTH = 1 << 12


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

        frames = austin.get_last_stack(thread_key).frames or []
        frame_stats = []
        max_scale = (
            system.max_memory
            if self._view.mode == AustinProfileMode.MEMORY
            else system.duration
        )

        def _add_frame_stats(
            stats: HierarchicalStats,
            marker: str,
            prefix: str,
            level: int = 0,
            active_bucket: Optional[dict] = None,
            active_parent: bool = True,
        ) -> None:
            if len(frame_stats) == MAX_LENGTH:
                frame_stats.append(
                    [
                        " " * 8,
                        " " * 8,
                        " " * 8,
                        " " * 8,
                        self._view.markup(
                            " <inactive>[truncated view; export the data to MOJO to see more with other tools]</inactive>"
                        ),
                    ]
                )
                return
            if len(frame_stats) > MAX_LENGTH:
                return
            if stats.total / 1e6 / max_scale < self._model.austin.threshold:
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

            column = (
                f":<lineno>{stats.label.column}</lineno>" if stats.label.column else ""
            )
            location = (
                (
                    (
                        escape(stats.label.function)
                        if active
                        else f"<inactive>{escape(stats.label.function)}</inactive>"
                    )
                    + f" <inactive>(<filename>{escape(stats.label.filename)}</filename>:<lineno>{stats.label.line}</lineno>{column})</inactive>"
                )
                if level < MAX_DEPTH
                else "<inactive>...</inactive>"
            )
            frame_stats.append(
                [
                    formatter(stats.own, active),
                    formatter(stats.total, active),
                    scaler(stats.own, max_scale, active),
                    scaler(stats.total, max_scale, active),
                    self._view.markup(f" <inactive>{marker}</inactive>{location}"),
                ]
            )

            if level >= MAX_DEPTH or not (
                children_stats := list(stats.children.values())
            ):
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

        pid, _, thread_name = thread_key.partition(":")
        iid, _, thread = thread_name.partition(":")
        thread_stats = austin.stats.processes[int(pid)].threads[
            ThreadName(thread, int(iid))
        ]
        if children := list(thread_stats.children.values()):
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
    ) -> FlameGraphData:
        thread_key = austin.threads[austin.current_thread]
        pid, _, thread_name = thread_key.partition(":")
        iid, _, thread = thread_name.partition(":")
        thread = austin.stats.processes[int(pid)].threads[ThreadName(thread, int(iid))]

        cs = {}  # type: ignore[var-annotated]
        total = thread.total
        total_pct = min(int(total / system.duration / 1e4), 100)
        data: FlameGraphData = {
            f"THREAD {thread.label.iid}:{thread.label.thread} ⏲️  {fmt_time(total)} ({total_pct}%)": (
                total,
                cs,
            )
        }
        levels = [(c, cs) for c in thread.children.values()]
        while levels:
            level, c = levels.pop(0)
            k = f"{level.label.function} ({level.label.filename})"
            if k in c:
                v, cs = c[k]
                c[k] = (v + level.total, cs)
            else:
                cs = {}
                c[k] = (level.total, cs)
            levels.extend(((c, cs) for c in level.children.values()))

        return data

    def update(self, data: FlameGraphData) -> bool:
        """Update the table."""
        (header,) = data
        return self._view.flamegraph.set_data(data) | self._view.graph_header.set_text(
            " FLAME GRAPH FOR " + header
        )
