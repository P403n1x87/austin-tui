# This file is part of "austin-tui" which is released under GPL.
#
# See file LICENCE or go to http://www.gnu.org/licenses/ for full license
# details.
#
# austin-tui is top-like TUI for Austin.
#
# Copyright (c) 2018-2020 Gabriele N. Tornetta <phoenix1987@gmail.com>.
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

import asyncio
import sys
from enum import Enum
from pathlib import Path
from textwrap import wrap
from time import time
from typing import Any
from typing import Callable
from typing import Optional
from typing import Sequence

from austin.aio import AsyncAustin
from austin.cli import AustinArgumentParser
from austin.cli import AustinCommandLineError
from austin.events import AustinMetadata
from austin.events import AustinSample
from austin.format.mojo import MojoStreamWriter
from psutil import Process

from austin_tui import AustinProfileMode
from austin_tui.adapters import Adapter
from austin_tui.adapters import CommandLineAdapter
from austin_tui.adapters import CountAdapter
from austin_tui.adapters import CpuAdapter
from austin_tui.adapters import CurrentThreadAdapter
from austin_tui.adapters import DurationAdapter
from austin_tui.adapters import FlameGraphAdapter
from austin_tui.adapters import MemoryAdapter
from austin_tui.adapters import ThreadDataAdapter
from austin_tui.adapters import ThreadFullDataAdapter
from austin_tui.adapters import ThreadNameAdapter
from austin_tui.adapters import ThreadTopDataAdapter
from austin_tui.model import Model
from austin_tui.view import ViewBuilder
from austin_tui.view.austin import AustinView
from austin_tui.view.austin import AustinViewMode
from austin_tui.widgets.markup import escape


class ThreadNav(Enum):
    """Thread navigation."""

    PREV = -1
    NEXT = 1


def _print(text: str) -> None:
    for line in wrap(text, 78):
        print(line, file=sys.stderr)


class AustinTUIArgumentParser(AustinArgumentParser):
    """Austin TUI implementation of the Austin argument parser."""

    def __init__(self) -> None:
        super().__init__(name="austin-tui", full=False)

    def parse_args(self) -> Any:
        """Parse command line arguments and report any errors."""
        try:
            return super().parse_args()
        except AustinCommandLineError as e:
            reason, *code = e.args
            if reason:
                _print(reason)
            exit(code[0] if code else -1)


class AustinTUIController:
    """Austin controller.

    This controller is in charge of Austin data managing and UI updates.
    """

    model = Model.get()  # type: ignore[assignment]

    cpu = CpuAdapter
    memory = MemoryAdapter
    duration = DurationAdapter
    samples = CountAdapter
    current_thread = CurrentThreadAdapter
    thread_name = ThreadNameAdapter
    thread_data = ThreadDataAdapter
    thread_full_data = ThreadFullDataAdapter
    thread_top_data = ThreadTopDataAdapter
    command_line = CommandLineAdapter
    flamegraph = FlameGraphAdapter

    def __init__(self) -> None:
        self._view_mode = AustinViewMode.LIVE
        self._scaler: Optional[Callable[..., Any]] = None
        self._formatter: Optional[Callable[..., Any]] = None
        self._last_timestamp = 0
        self._update_task: Optional[asyncio.Task[None]] = None
        self._exception: Optional[Exception] = None

        view_builder = ViewBuilder.from_resource(
            "austin_tui.view", "tui.austinui"
        )

        self.austin: Optional[AsyncAustin] = None
        self.view: AustinView = view_builder.build()  # type: ignore[assignment]
        view = self.view
        self.view.callback = self.on_view_event

        view_builder.autoconnect(self)

        self.model.austin.mode = view.mode

        # Auto-create adapters
        for name, adapter_class in (
            (n, v)
            for n, v in type(self).__dict__.items()
            if isinstance(v, type) and v.__mro__[-2] == Adapter
        ):
            setattr(self, name, adapter_class(self.model, self.view))

    def set_thread_data(self) -> None:
        """Set the thread stack."""
        if not self.model.austin.threads:
            return

        if self._view_mode is AustinViewMode.GRAPH:
            self.flamegraph()  # type: ignore[call-arg]
        elif self._view_mode is AustinViewMode.FULL:
            self.thread_full_data()  # type: ignore[call-arg]
        elif self._view_mode is AustinViewMode.TOP:
            self.thread_top_data()  # type: ignore[call-arg]
        else:
            self.thread_data()  # type: ignore[call-arg]

        # self._last_timestamp = self.model.austin.stats.timestamp

    def set_thread(self) -> bool:
        """Set the thread to display."""
        self.current_thread()  # type: ignore[call-arg]
        self.thread_name()

        if not self.model.austin.threads:
            return True

        # Populate the thread stack view
        self.set_thread_data()

        return True

    def _add_flamegraph_palette(self) -> None:
        colors = [196, 202, 214, 124, 160, 166, 208]
        palette = self.view.palette

        for i, color in enumerate(colors):
            palette.add_color(f"fg{i}", 15, color)
            palette.add_color(f"fgf{i}", color)

        self.view.flamegraph.set_palette(
            (
                [palette.get_color(f"fg{i}") for i in range(len(colors))],
                [palette.get_color(f"fgf{i}") for i in range(len(colors))],
            )
        )

    async def start(self, args: Sequence[str]) -> None:
        """Start event."""
        pargs = AustinTUIArgumentParser().parse_args()  # type: ignore[call-arg]

        self.austin = AsyncAustin(self.on_sample, self.on_metadata, self.on_terminate)

        await self.austin.start(args)

        if pargs.pid is not None:
            child_process = Process(pargs.pid)
        else:
            austin_process = Process(self.austin._proc.pid)
            (child_process,) = austin_process.children()
        command = child_process.cmdline()

        mode = AustinProfileMode.MEMORY if pargs.memory else AustinProfileMode.TIME
        self.view.mode = mode

        """Austin ready callback."""
        self.model.system.set_child_process(child_process)
        # self.model.austin.set_metadata(self._meta)
        self.model.austin.set_command_line(command)

        self._add_flamegraph_palette()
        self.view.open()
        self._update_task = asyncio.create_task(self.update_loop())

        self._formatter, self._scaler = (
            (self.view.fmt_mem, self.view.scale_memory)
            if self.view.mode == AustinProfileMode.MEMORY
            else (self.view.fmt_time, self.view.scale_time)
        )
        self.model.system.start()

        self.command_line()

        self.view.set_pid(child_process.pid, pargs.children)

        try:
            await self.austin.wait()
        except Exception:
            self.shutdown()
            raise

        try:
            if self.view._input_task is not None:
                await self.view._input_task
        except asyncio.CancelledError:
            pass
        except Exception:
            self.shutdown()
            raise

        if self._exception is not None:
            raise self._exception

    async def stop(self) -> None:
        """Called when Austin exits: cancel the update task and mark the view stopped.

        Does not close the view — the user can still review final stats and press Q.
        """
        self.model.system.stop()

        if self._update_task is not None:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
            except Exception as exc:
                self._exception = exc
            self._update_task = None

        self.view.stop()

    def update(self) -> bool:
        """Update event."""
        if self.model.frozen:
            return False

        # System data
        self.duration()
        self.cpu()  # type: ignore[call-arg]
        self.memory()  # type: ignore[call-arg]

        # Samples count
        self.samples()

        if self.model.austin.stats.timestamp > self._last_timestamp:
            return self.set_thread()

        return False

    async def update_loop(self) -> None:
        """The UI update loop."""
        try:
            while (
                not self.view._stopped
                and self.view.is_open
                and self.view.root_widget
            ):
                if self.update():
                    if self._view_mode is AustinViewMode.GRAPH:
                        self.view.flamegraph.draw()
                    else:
                        self.view.table.draw()

                self.view.root_widget.refresh()

                try:
                    await asyncio.sleep(1)
                except asyncio.CancelledError:
                    break
        except Exception as exc:
            self.view.on_exception(exc)

    def _change_thread(self, direction: ThreadNav) -> bool:
        """Change thread."""
        austin = (
            self.model.frozen_austin or self.model.austin
            if self.model.frozen
            else self.model.austin
        )
        prev_index = austin.current_thread

        austin.current_thread = max(
            0,
            min(
                austin.current_thread + direction.value,
                len(austin.threads) - 1,
            ),
        )

        if prev_index != austin.current_thread:
            return self.set_thread()

        return False

    async def on_next_thread(self) -> bool:
        """Handle next thread event."""
        if self._change_thread(ThreadNav.NEXT):
            if self._view_mode is AustinViewMode.GRAPH:
                self.view.flamegraph.draw()
                self.view.flame_view.refresh()
            else:
                self.view.table.draw()
                self.view.stats_view.refresh()
            return True
        return False

    async def on_previous_thread(self) -> bool:
        """Handle previous thread event."""
        if self._change_thread(ThreadNav.PREV):
            if self._view_mode is AustinViewMode.GRAPH:
                self.view.flamegraph.draw()
                self.view.flame_view.refresh()
            else:
                self.view.table.draw()
                self.view.stats_view.refresh()
            return True
        return False

    async def on_live_mode_selected(self, _: Any = None) -> bool:
        """Select live mode."""
        if self._view_mode is AustinViewMode.LIVE:
            return False

        self._view_mode = AustinViewMode.LIVE
        self.view.dataview_selector.select(0)
        self.set_thread_data()

        self.view.table.draw()
        self.view.stats_view.refresh()

        return True

    async def on_top_mode_selected(self, _: Any = None) -> bool:
        """Select top mode."""
        if self._view_mode is AustinViewMode.TOP:
            return False

        self._view_mode = AustinViewMode.TOP
        self.view.dataview_selector.select(0)
        self.set_thread_data()

        self.view.table.draw()
        self.view.stats_view.refresh()

        return True

    async def on_full_mode_selected(self, _: Any = None) -> bool:
        """Toggle full mode."""
        if self._view_mode is AustinViewMode.FULL:
            return False

        self._view_mode = AustinViewMode.FULL
        self.view.dataview_selector.select(0)
        self.set_thread_data()

        self.view.table.draw()
        self.view.stats_view.refresh()

        return True

    async def on_save(self, _: Any = None) -> bool:
        """Save the collected stats."""
        model = (
            self.model.frozen_austin if self.model.frozen else self.model.austin
        )

        def _dump_stats() -> None:
            assert self.model.system.child_process is not None
            pid = self.model.system.child_process.pid
            output_file = Path(f"austin_{int(time())}_{pid}").with_suffix(
                ".mojo"
            )
            try:
                with output_file.open("wb") as stream:
                    mojo_writer = MojoStreamWriter(stream)
                    for k, v in model.metadata.items():
                        mojo_writer.write(AustinMetadata(k, v))
                    for event in model.stats.flatten():
                        mojo_writer.write(event)
                self.view.notification.set_text(
                    self.view.markup(
                        f"Stats saved as <running>{escape(str(output_file))}</running> "
                    )
                )
            except IOError as e:
                self.view.notification.set_text(f"Failed to save stats: {e}")

            self.view.root_widget.refresh()

        await asyncio.get_event_loop().run_in_executor(None, _dump_stats)

        return False

    async def on_play_pause(self, _: Any = None) -> bool:
        """On play/pause handler."""
        if self.view._stopped:
            return False

        self.model.toggle_freeze()
        self.update()
        self.view.notification.set_text(
            "Paused" if self.model.frozen else "Resumed"
        )
        return True

    def _change_threshold(self, delta: float) -> float:
        self.model.austin.threshold += delta

        if self.model.austin.threshold < 0.0:
            self.model.austin.threshold = 0.0
        elif self.model.austin.threshold > 1.0:
            self.model.austin.threshold = 1.0

        if self.view._stopped or self.model.frozen:
            self.set_thread_data()
            self.view.table.draw()
            self.view.table.refresh()

        return self.model.austin.threshold

    async def on_threshold_up(self, _: Any = None) -> bool:
        """Handle threshold up."""
        th = self._change_threshold(0.01) * 100.0
        self.view.threshold.set_text(f"{th:.0f}%")
        return True

    async def on_threshold_down(self, _: Any = None) -> bool:
        """Handle threshold down."""
        th = self._change_threshold(-0.01) * 100.0
        self.view.threshold.set_text(f"{th:.0f}%")
        return True

    async def on_graph_selected(self, _: Any = None) -> bool:
        """Select graph visualisation."""
        if self._view_mode is AustinViewMode.GRAPH:
            return False

        self._view_mode = AustinViewMode.GRAPH

        self.view.dataview_selector.select(1)

        self.flamegraph()  # type: ignore[call-arg]

        return True

    def shutdown(self) -> None:
        """Force quit: terminate Austin and close the view immediately."""
        try:
            if self.austin is not None:
                self.austin.terminate()
        except Exception:
            pass
        try:
            self.view.close()
        except Exception:
            pass

    def on_shutdown(self, _: Any = None) -> None:
        """The shutdown view event handler."""
        self.shutdown()

    def on_exception(self, exc: Exception) -> None:
        """The exception view event handler."""
        self.shutdown()
        raise exc

    # Austin events

    async def on_sample(self, sample: AustinSample) -> None:
        """Austin sample received callback."""
        self.model.austin.update(sample)

    async def on_metadata(self, metadata: AustinMetadata) -> None:
        """Austin metadata received callback."""
        if metadata.name == "mode":
            self.view.set_mode(metadata.value)
        elif metadata.name == "python":
            self.view.set_python(metadata.value)
        # else:
        #     self.model.austin.set_metadata(self._meta)

    async def on_terminate(self) -> None:
        """Austin terminate callback."""
        await self.stop()

    # View events

    def on_view_event(self, event: AustinView.Event, data: Any = None) -> None:
        """View events handler."""

        def _unhandled(_: Any) -> None:
            raise RuntimeError(f"Unhandled view event: {event}")

        {
            AustinView.Event.QUIT: self.on_shutdown,
            AustinView.Event.EXCEPTION: self.on_exception,
        }.get(event, _unhandled)(data)  # type: ignore[operator]
