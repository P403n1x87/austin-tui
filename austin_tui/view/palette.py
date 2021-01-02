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
from typing import Dict, Tuple


class PaletteError(Exception):
    """Palette generic error."""

    pass


class Palette:
    """Palette object.

    This is essentially a wrapper around the concept of curses color pairs.
    """

    def __init__(self) -> None:
        self._colors = {"default": 0}
        self._color_pairs: Dict[int, Tuple[int, int]] = {}

    def add_color(self, name: str, fg: int = -1, bg: int = -1) -> None:
        """Add a color pair to the palette."""
        color_id = len(self._colors)
        self._colors[name] = color_id
        self._color_pairs[color_id] = (int(fg), int(bg))

    def get_color(self, name: str) -> int:
        """Get the color by name."""
        try:
            return getattr(self, name)
        except KeyError:
            raise PaletteError(f"The palette has no color '{name}'")

    def __getattr__(self, name: str) -> int:
        """Convenience accessor for colors from the palette."""
        return self._colors[name]

    def init(self) -> None:
        """Initialise the curses color pairs."""
        try:
            for cid, pair in self._color_pairs.items():
                curses.init_pair(cid, *pair)
        except curses.error:
            pass
