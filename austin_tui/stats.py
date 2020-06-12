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

import copy
from collections import deque
from threading import RLock

ATOM_LOCK = RLock()


def atomic(f):
    """Decorator to turn a function into an atomic operation."""

    def atomic_wrapper(*args, **kwargs):
        with ATOM_LOCK:
            result = f(*args, **kwargs)

        return result

    return atomic_wrapper


class Stats:
    """
    Statistics class. Each instance will bear statistics for each sampling run.

    To update the statistics, simply pass every single line returned by austin
    to an instance of this class via the `add_thread_sample` method.

    To retrieve the current stacks along with their statistics, call the
    `get_current_stacks` methods.
    """

    def __init__(self):
        self.threads = {}
        self.current_thread = None
        self.current_stack = None
        self.current_threads = {}
        self.samples = 0

    def _update_frame(self, frame_stack, sample_stack):
        if sample_stack is None:
            return

        frame_stack.total_time += sample_stack.total_time
        frame_stack.own_time += sample_stack.own_time

        if sample_stack.children:
            sample_child = sample_stack.children[0]

            i = 0
            for child in frame_stack.children:
                if child == sample_child:
                    self._update_frame(child, sample_child)
                    break
                i += 1
            else:
                frame_stack.children.append(sample_child)

            self.current_stack.appendleft(i)

    @atomic
    def add_thread_sample(self, collapsed_sample):
        process, thread, frames, (duration,) = parse_line(collapsed_sample)

        sample_stack = SampledFrame(frames, duration, 1) if frames else None

        self.current_stack = deque()

        i = 0
        thread_id = (
            f"{process.split()[1]}:{thread.split()[1]}"
            if process
            else thread.split()[1]
        )
        if thread_id in self.threads:
            for frame_stack in self.threads[thread_id]:
                if frame_stack == sample_stack:
                    self._update_frame(frame_stack, sample_stack)
                    break
                i += 1
            else:
                self.threads[thread_id].append(sample_stack)

        else:
            self.threads[thread_id] = [sample_stack]

        self.current_stack.appendleft(i)

        self.current_threads[thread_id] = self.current_stack

        self.samples += 1

    @atomic
    def get_current_stacks(self, reset_after=False):
        stacks = {}
        for thread in self.current_threads:
            frame_list = self.threads[thread]
            stack = []
            for i in self.current_threads[thread]:
                if frame_list[i] is None:
                    continue
                stack.append(frame_list[i].to_dict())
                frame_list = frame_list[i].children
            stacks[thread] = stack

        if reset_after:
            self.current_threads = {}

        return stacks

    @atomic
    def get_current_threads(self):
        return sorted(self.current_threads.keys())

    @atomic
    def get_thread_stack(self, thread):
        if thread not in self.current_threads:
            return None

        retval = copy.deepcopy(self.threads[thread])

        frame_list = retval
        for i in self.current_threads[thread]:
            if frame_list[i]:
                frame_list[i].is_active = True
                frame_list = frame_list[i].children
            else:
                break

        return retval
