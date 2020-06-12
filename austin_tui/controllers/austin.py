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

from enum import Enum

from austin_tui.controllers import Controller, Event
from austin_tui.controllers.system import fmt_time as _fmt_time  # TODO: remove
from austin_tui.models import AustinModel
from austin_tui.view.palette import Color
from austin_tui.widgets.markup import AttrStringChunk, am, escape


class AustinProfileMode(Enum):
    TIME = "Time"
    MEMORY = "Memory"


class ThreadNav(Enum):
    PREV = -1
    NEXT = 1


class AustinEvent(Event):
    START = "on_start"
    UPDATE = "on_update"
    CHANGE_THREAD = "on_change_thread"
    TOGGLE_FULL_MODE = "on_toggle_full_mode"


def fmt_time(t, active=True):
    return AttrStringChunk(
        f" {_fmt_time(t):^6} ", color=Color.INACTIVE if not active else None
    )


def fmt_mem(s, active=True):
    return AttrStringChunk(
        f" {int(s)>>10: 5d}M ", color=Color.INACTIVE if not active else None
    )


def color_level(p, a=True):
    d = 10 if a else 20
    return d + int(p / 20 - 0.5)


def _scaler(ratio, active):
    return AttrStringChunk(f" {ratio:5.1f}% ", color=color_level(ratio, active))


def scale_memory(memory, max_memory, active=True):
    return _scaler((memory >> 10) / max_memory * 100, active)


def scale_time(time, duration, active=True):
    return _scaler(min(time / 1e4 / duration, 100), active)


class AustinController(Controller):

    __model__ = AustinModel

    def __init__(self, view):
        super().__init__(view)

        self._thread_index = 0
        self._full_mode = False
        self._scaler = None
        self._formatter = None

    def set_current_stack(self):
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
                    am(
                        " "
                        + escape(child_frame_stats.label.function)
                        + f" <inactive>({escape(child_frame_stats.label.filename)}:{child_frame_stats.label.line})</inactive>"
                    ),
                ]
            )
            container = child_frame_stats.children

        self.view.table_pad.set_data(frame_stats)

    def set_full_thread_stack(self):
        thread_key = self.model.threads[self._thread_index]
        pid, _, thread = thread_key.partition(":")

        frames = self.model.get_last_stack(thread_key).frames
        frame_stats = []
        max_scale = (
            self.view._system_controller.model.max_memory
            if self.view.mode == AustinProfileMode.MEMORY
            else self.view._system_controller.model.duration
        )

        def add_frame_stats(stats, marker, prefix, level=0, active_bucket=None):
            try:
                active = stats.label in active_bucket and stats.label == frames[level]
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
                    am(
                        " "
                        + f"<inactive>{marker}</inactive>"
                        + (
                            escape(stats.label.function)
                            if active
                            else f"<inactive>{escape(stats.label.function)}</inactive>"
                        )
                        + f" <inactive>({escape(stats.label.filename)}:{stats.label.line})</inactive>"
                    ),
                ]
            )
            children_stats = [child_stats for _, child_stats in stats.children.items()]
            if not children_stats:
                return
            for child_stats in children_stats[:-1]:
                add_frame_stats(
                    child_stats,
                    prefix + "├─ ",
                    prefix + "│  ",
                    level + 1,
                    active_bucket,
                )

            add_frame_stats(
                children_stats[-1],
                prefix + "└─ ",
                prefix + "   ",
                level + 1,
                active_bucket,
            )

        thread_stats = self.model.stats.processes[int(pid)].threads[thread]

        children = [stats for _, stats in thread_stats.children.items()]
        if children:
            for stats in children[:-1]:
                add_frame_stats(stats, "├─ ", "│  ", 0, thread_stats.children)

            add_frame_stats(children[-1], "└─ ", "   ", 0, thread_stats.children)

        self.view.table_pad.set_data(frame_stats)

    def set_thread_stack(self):
        if not self.model.threads:
            return

        if self._full_mode:
            self.set_full_thread_stack()
        else:
            self.set_current_stack()

    def set_thread(self):
        if not self.model.threads:
            self.view.thread_num.set_text("--")
            return

        # Set thread number
        self.view.thread_num.set_text(self._thread_index + 1)

        # Set thread name
        pid, _, thread_id = self.model.threads[self._thread_index].partition(":")
        self.view.thread_name.set_text((f"{pid}:" if int(pid) else "") + thread_id)

        # Populate the thread stack view
        self.set_thread_stack()

    def on_start(self, data=None):
        self._formatter, self._scaler = (
            (fmt_mem, scale_memory)
            if self.view.mode == AustinProfileMode.MEMORY
            else (fmt_time, scale_time)
        )

    def on_update(self, data=None):
        # Samples count
        self.view.samples.set_text(self.model.samples_count)

        # Count total threads (across processes)
        self.view.thread_total.set_text(len(self.model.threads))

        self.set_thread()

    def on_change_thread(self, direction: ThreadNav):
        prev_index = self._thread_index

        self._thread_index = max(
            0, min(self._thread_index + direction.value, len(self.model.threads) - 1)
        )

        if prev_index != self._thread_index:
            self.set_thread()

    def on_toggle_full_mode(self, data=None):
        self._full_mode = not self._full_mode
        self.set_thread_stack()
