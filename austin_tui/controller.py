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
from enum import Enum
from io import StringIO
from time import time
from typing import Any

from austin_tui import AustinProfileMode
from austin_tui.adapters import Adapter
from austin_tui.adapters import CountAdapter
from austin_tui.adapters import CpuAdapter
from austin_tui.adapters import CurrentThreadAdapter
from austin_tui.adapters import DurationAdapter
from austin_tui.adapters import MemoryAdapter
from austin_tui.adapters import ThreadDataAdapter
from austin_tui.adapters import ThreadFullDataAdapter
from austin_tui.adapters import ThreadNameAdapter
from austin_tui.adapters import ThreadTotalAdapter
from austin_tui.model import Model
from austin_tui.view import ViewBuilder


class ThreadNav(Enum):
    """Thread navigation."""

    PREV = -1
    NEXT = 1


class AustinTUIController:
    """Austin controller.

    This controller is in charge of Austin data managing and UI updates.
    """

    model = Model.get()  # type: ignore[assignment]

    cpu = CpuAdapter
    memory = MemoryAdapter
    duration = DurationAdapter
    samples = CountAdapter
    threads = ThreadTotalAdapter
    current_thread = CurrentThreadAdapter
    thread_name = ThreadNameAdapter
    thread_data = ThreadDataAdapter
    thread_full_data = ThreadFullDataAdapter

    def __init__(self) -> None:
        self._full_mode = False
        self._scaler = None
        self._formatter = None
        self._last_timestamp = 0

        view_builder = ViewBuilder.from_resource("austin_tui.view", "tui.austinui")

        self.view = view = view_builder.build()  # type: ignore[assignment]

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

        if self._full_mode:
            self.thread_full_data()  # type: ignore[call-arg]
        else:
            self.thread_data()  # type: ignore[call-arg]

        self._last_timestamp = self.model.austin.stats.timestamp

    def set_thread(self) -> bool:
        """Set the thread to display."""
        self.current_thread()  # type: ignore[call-arg]
        self.thread_name()

        if not self.model.austin.threads:
            return True

        # Populate the thread stack view
        self.set_thread_data()

        return True

    def start(self) -> None:
        """Start event."""
        self.view.open()
        self.view.submit_task(self.update_loop())

        self._formatter, self._scaler = (
            (self.view.fmt_mem, self.view.scale_memory)
            if self.view.mode == AustinProfileMode.MEMORY
            else (self.view.fmt_time, self.view.scale_time)
        )
        self.model.system.start()

    def stop(self) -> None:
        """Stop event."""
        self.model.system.stop()

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

        # Count total threads (across processes)
        self.threads()

        if self.model.austin.stats.timestamp > self._last_timestamp:
            return self.set_thread()

        return False

    async def update_loop(self) -> None:
        """The UI update loop."""
        while not self.view._stopped and self.view.is_open and self.view.root_widget:
            if self.update():
                self.view.table.draw()

            self.view.root_widget.refresh()

            await asyncio.sleep(1)

    def _change_thread(self, direction: ThreadNav) -> bool:
        """Change thread."""
        austin = self.model.frozen_austin if self.model.frozen else self.model.austin
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
            self.view.table.draw()
            self.view.stats_view.refresh()
            return True
        return False

    async def on_previous_thread(self) -> bool:
        """Handle previous thread event."""
        if self._change_thread(ThreadNav.PREV):
            self.view.table.draw()
            self.view.stats_view.refresh()
            return True
        return False

    async def on_full_mode_toggled(self, _: Any = None) -> bool:
        """Toggle full mode."""
        self._full_mode = not self._full_mode
        self.set_thread_data()

        self.view.table.draw()
        self.view.stats_view.refresh()

        return True

    async def on_save(self, _: Any = None) -> bool:
        """Save the collected stats."""
        model = self.model.frozen_austin if self.model.frozen else self.model.austin

        def _dump_stats() -> None:
            pid = self.model.system.child_process.pid
            filename = f"austin_{int(time())}_{pid}.aprof"
            try:
                buffer = StringIO()
                model.stats.dump(buffer)
                with open(filename, "w") as fout:
                    fout.write(buffer.getvalue().replace(" 0 0\n", "\n"))
                self.view.notification.set_text(
                    self.view.markup(f"Stats saved as <running>{filename}</running> 📝 ")
                )
            except IOError as e:
                self.view.notification.set_text(f"Failed to save stats: {e}")

            self.view.root_widget.refresh()

        self.view.submit_task(_dump_stats)

        return False

    async def on_play_pause(self, _: Any = None) -> bool:
        """On play/pause handler."""
        if self.view._stopped:
            return False

        self.model.toggle_freeze()
        self.update()
        self.view.notification.set_text("Paused" if self.model.frozen else "Resumed")
        return True
