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

import time

from austin_tui.models import Model
from psutil import NoSuchProcess, Process


Seconds = float
Percentage = float
Bytes = int


class SystemModel(Model):
    """System statistics model."""

    def __init__(self) -> None:
        self._start_time: Seconds = 0
        self._end_time: Seconds = 0

        self._max_mem: Bytes = 0

    def start(self) -> None:
        """Start the model."""
        self._start_time = time.time()

    def stop(self) -> None:
        """Stop the model."""
        self._end_time = time.time()

    @property
    def duration(self) -> Seconds:
        """Get the sampling duration."""
        return (
            (self._end_time or time.time()) - self._start_time
            if self._start_time
            else 0
        )

    def get_cpu(self, process: Process) -> Percentage:
        """Get the process CPU usage."""
        try:
            return int(process.cpu_percent())
        except NoSuchProcess:
            return 0

    def get_memory(self, process: Process) -> Bytes:
        """Get the process memory."""
        try:
            mem = process.memory_full_info()[0]
            self._max_mem = max(mem, self._max_mem)
            return mem
        except NoSuchProcess:
            return 0

    @property
    def max_memory(self) -> Bytes:
        """Return the maximum memory usage seen so far."""
        return self._max_mem
