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


class PaletteError(Exception):
    pass


class Palette:
    def __init__(self):
        self._colors = {"default": 0}
        self._color_pairs = {}

    def add_color(self, name, fg=-1, bg=-1):
        color_id = len(self._colors)
        self._colors[name] = color_id
        self._color_pairs[color_id] = (int(fg), int(bg))

    def get_color(self, name):
        try:
            return getattr(self, name)
        except KeyError:
            raise PaletteError(f"The palette has no color '{name}'")

    def __getattr__(self, name):
        return self._colors[name]

    def init(self):
        for cid, pair in self._color_pairs.items():
            curses.init_pair(cid, *pair)
