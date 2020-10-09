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

from austin.stats import ThreadStats
from austin_tui.controllers import Controller, Event
from austin_tui.models import AustinModel
from austin_tui.view import View
from austin_tui.widgets.markup import escape


class AustinProfileMode(Enum):
    """Austin profile modes."""

    TIME = "Time"
    MEMORY = "Memory"


class ThreadNav(Enum):
    """Thread navigation."""

    PREV = -1
    NEXT = 1


class AustinEvent(Event):
    """Austin controller events."""

    START = "on_start"
    UPDATE = "on_update"
    CHANGE_THREAD = "on_change_thread"
    TOGGLE_FULL_MODE = "on_toggle_full_mode"
    SAVE = "on_save"


class AustinController(Controller):
    """Austin controller.

    This controller is in charge of Austin data managing and UI updates.
    """

    __model__ = AustinModel

    def __init__(self, view: View) -> None:
        super().__init__(view)

        self._thread_index = 0
        self._full_mode = False
        self._scaler = None
        self._formatter = None
        self._last_timestamp = 0

    def set_current_stack(self) -> None:
        """Set the current stack."""
        if not self._formatter or not self._scaler:
            raise RuntimeError(
                "Inconsistent state: either formatter or scaler not set."
            )
        thread_key = self.model.threads[self._thread_index]
        pid, _, thread = thread_key.partition(":")

        thread_stats = self.model.stats.processes[int(pid)].threads[thread]
        frames = self.model.get_last_stack(thread_key).frames

        container = thread_stats.children
        frame_stats = []
        max_scale = (
            self.view._system_controller.model.max_memory
            if self.view.mode == AustinProfileMode.MEMORY
            else self.view._system_controller.model.duration
        )
        for frame in frames:
            child_frame_stats = container[frame]
            frame_stats.append(
                [
                    self._formatter(child_frame_stats.own.time),
                    self._formatter(child_frame_stats.total.time),
                    self._scaler(child_frame_stats.own.time, max_scale),
                    self._scaler(child_frame_stats.total.time, max_scale),
                    self.view.markup(
                        " "
                        + escape(child_frame_stats.label.function)
                        + f" <inactive>({escape(child_frame_stats.label.filename)}"
                        f":{child_frame_stats.label.line})</inactive>"
                    ),
                ]
            )
            container = child_frame_stats.children

        self.view.table.set_data(frame_stats)

    def set_full_thread_stack(self) -> None:
        """Set the full thread stack."""
        if not self._formatter or not self._scaler:
            raise RuntimeError(
                "Inconsistent state: either formatter or scaler not set."
            )
        thread_key = self.model.threads[self._thread_index]
        pid, _, thread = thread_key.partition(":")

        frames = self.model.get_last_stack(thread_key).frames
        frame_stats = []
        max_scale = (
            self.view._system_controller.model.max_memory
            if self.view.mode == AustinProfileMode.MEMORY
            else self.view._system_controller.model.duration
        )

        def _add_frame_stats(
            stats: ThreadStats,
            marker: str,
            prefix: str,
            level: int = 0,
            active_bucket: dict = None,
            active_parent: bool = True,
        ) -> None:
            try:
                active = (
                    stats.label in active_bucket
                    and stats.label == frames[level]
                    and active_parent
                )
                active_bucket = stats.children
            except (IndexError, TypeError):
                active = False
                active_bucket = None

            frame_stats.append(
                [
                    self._formatter(stats.own.time, active),
                    self._formatter(stats.total.time, active),
                    self._scaler(stats.own.time, max_scale, active),
                    self._scaler(stats.total.time, max_scale, active),
                    self.view.markup(
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

        thread_stats = self.model.stats.processes[int(pid)].threads[thread]

        children = [stats for _, stats in thread_stats.children.items()]
        if children:
            for stats in children[:-1]:
                _add_frame_stats(stats, "├─ ", "│  ", 0, thread_stats.children)

            _add_frame_stats(children[-1], "└─ ", "   ", 0, thread_stats.children)

        self.view.table.set_data(frame_stats)

    def set_thread_stack(self) -> None:
        """Set the thread stack."""
        if not self.model.threads:
            return

        if self._full_mode:
            self.set_full_thread_stack()
        else:
            self.set_current_stack()

        self._last_timestamp = self.model.stats.timestamp

    def set_thread(self) -> bool:
        """Set the thread to display."""
        if not self.model.threads:
            self.view.thread_num.set_text("--")
            return True

        # Set thread number
        self.view.thread_num.set_text(self._thread_index + 1)

        # Set thread name
        pid, _, thread_id = self.model.threads[self._thread_index].partition(":")
        self.view.thread_name.set_text((f"{pid}:" if int(pid) else "") + thread_id)

        # Populate the thread stack view
        self.set_thread_stack()

        return True

    def on_start(self, data: Any = None) -> None:
        """Start event."""
        self._formatter, self._scaler = (
            (self.view.fmt_mem, self.view.scale_memory)
            if self.view.mode == AustinProfileMode.MEMORY
            else (self.view.fmt_time, self.view.scale_time)
        )

    def on_update(self, data: Any = None) -> bool:
        """Update event."""
        # Samples count
        self.view.samples.set_text(self.model.samples_count)

        # Count total threads (across processes)
        self.view.thread_total.set_text(len(self.model.threads))

        if self.model.stats.timestamp > self._last_timestamp:
            return self.set_thread()

        return False

    def on_change_thread(self, direction: ThreadNav) -> bool:
        """Change thread."""
        prev_index = self._thread_index

        self._thread_index = max(
            0, min(self._thread_index + direction.value, len(self.model.threads) - 1)
        )

        if prev_index != self._thread_index:
            return self.set_thread()

        return False

    def on_toggle_full_mode(self, data: Any = None) -> None:
        """Toggle full mode."""
        self._full_mode = not self._full_mode
        self.set_thread_stack()

    def on_save(self, data: Any = None) -> bool:
        """Save the collected stats."""

        def _dump_stats() -> None:
            pid = self.view._system_controller._child_proc.pid
            filename = f"austin_{int(time())}_{pid}.aprof"
            try:
                buffer = StringIO()
                self.model.stats.dump(buffer)
                with open(filename, "w") as fout:
                    fout.write(buffer.getvalue().replace(" 0 0\n", "\n"))
                self.view.notification.set_text(
                    self.view.markup(f"Stats saved as <running>{filename}</running> 📝 ")
                )
            except IOError as e:
                self.view.notification.set_text(f"Failed to save stats: {e}")

        asyncio.get_event_loop().run_in_executor(None, _dump_stats)

        return True
