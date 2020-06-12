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

import curses
from typing import Any


class Color:
    INACTIVE = 1
    HEAT_ACTIVE = 10
    HEAT_INACTIVE = 20
    RUNNING = 2
    STOPPED = 3
    CPU = 4
    MEMORY = 5
    THREAD = 6


PALETTE = {
    Color.INACTIVE: (246, -1),
    Color.RUNNING: (10, -1),
    Color.STOPPED: (1, -1),
    Color.CPU: (curses.COLOR_BLUE, -1),  # 17
    Color.MEMORY: (curses.COLOR_GREEN, -1),  # 22
    Color.THREAD: (11, -1),  # 22
}


def init():
    for color, values in PALETTE.items():
        curses.init_pair(color, *values)

    j = Color.HEAT_ACTIVE
    for i in [-1, 226, 208, 202, 196]:
        curses.init_pair(j, i, -1)
        j += 1
    j = Color.HEAT_INACTIVE
    for i in [246, 100, 130, 94, 88]:
        curses.init_pair(j, i, -1)
        j += 1
