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

from typing import Any

from austin_tui.controllers import Controller, Event
from austin_tui.models import SystemModel
from psutil import Process


def fmt_time(s: int) -> str:
    """Format microseconds into mm':ss''."""
    m = int(s // 60e6)
    ret = '{:02d}"'.format(round(s / 1e6) % 60)
    if m:
        ret = str(m) + "'" + ret

    return ret


class SystemEvent(Event):
    """System controller events."""

    START = "on_start"
    UPDATE = "on_update"
    STOP = "on_stop"


class SystemController(Controller):
    """System controller.

    This controller is in charge of the system model and of UI updates with
    fresh system data (e.g. CPU usage, duration etc...).
    """

    __model__ = SystemModel

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._child_proc = None

    def set_child_process(self, child_process: Process) -> None:
        """Set the child process."""
        self._child_proc = child_process

    def on_start(self, data: Any = None) -> None:
        """Start event."""
        self.model.start()

    def on_stop(self, data: Any = None) -> None:
        """Stop event."""
        self.model.stop()

    def on_update(self, data: Any = None) -> None:
        """Update the UI with system data."""
        self.view.duration.set_text(fmt_time(int(self.model.duration * 1e6)))

        cpu = self.model.get_cpu(self._child_proc)
        self.view.cpu.set_text(f"{cpu}% ")
        self.view.cpu_plot.push(cpu)

        mem = self.model.get_memory(self._child_proc)

        self.view.mem.set_text(f"{mem>>20}M ")
        self.view.mem_plot.push(mem)
