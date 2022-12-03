# This file is part of "austin-tui" which is released under GPL.
#
# See file LICENCE or go to http://www.gnu.org/licenses/ for full license
# details.
#
# austin-tui is top-like TUI for Austin.
#
# Copyright (c) 2018-2022 Gabriele N. Tornetta <phoenix1987@gmail.com>.
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
from random import randrange
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from austin_tui.widgets import Rect
from austin_tui.widgets import Widget


FlameGraphData = Dict[str, Tuple[float, "FlameGraphData"]]  # type: ignore[misc]


class FlameGraph(Widget):
    """Flame graph widget."""

    def __init__(self, name: str) -> None:
        super().__init__(name)

        self._data: Optional[dict] = None
        self._height = 40
        self._palette: Optional[Tuple[List[int], List[int]]] = None

    def set_palette(self, palette: Tuple[List[int], List[int]]) -> None:
        """Set the flame graph palette."""
        self._palette = palette

    def resize(self, rect: Rect) -> bool:
        """Resize the table."""
        if self.rect == rect:
            return False

        self.rect = rect

        self.draw()

        return True

    def set_data(self, data: dict) -> bool:
        """Set the graph data."""

        def h(s: dict, scale: float) -> int:
            if not s:
                return 1

            return 1 + max(
                (
                    h(c, scale)
                    for c in (_[1] for _ in s.values() if _[0] * scale * 8 >= 1)
                ),
                default=0,
            )

        if data != self._data:
            self._data = data

            w = self.size.x
            for _, (v, _) in self._data.items():
                scale = w / v

            self._height = h(data, scale)
            self.parent.resize(self.parent.rect)
            return True

        return False

    def _draw_frame(self, x: int, y: int, w: float, text: str) -> None:
        win = self.win.get_win()

        iw = int(w)
        fw = int((w - iw) * 8)

        assert self._palette is not None, self._palette
        fg, fgf = self._palette

        i = randrange(0, len(fg))

        color = curses.color_pair(fg[i])
        fcolor = curses.color_pair(fgf[i])

        try:
            win.addstr(y, x, " " * iw, color)
        except curses.error:
            pass
        if fw:
            c = ["", "▏", "▎", "▍", "▌", "▋", "▊", "▉"][fw]
            try:
                win.addstr(y, x + iw, c, fcolor)
            except curses.error:
                pass
        if iw > 4:
            if len(text) > iw - 2:
                _text = text[: iw - 4] + ".."
            else:
                _text = text
            win.addstr(y, x, " " + _text, color)

    def draw(self) -> bool:
        """Draw the graph."""
        super().draw()

        if not self.win or not self._data:
            return False

        self.win.get_win().clear()

        w = self.size.x
        for _, (v, _) in self._data.items():
            scale = w / v

        levels = [(0, -1, (k, v)) for k, v in self._data.items()]
        while levels:
            x, y, (f, (v, cs)) = levels.pop(0)
            w = v * scale
            if y >= 0:
                self._draw_frame(x, y, w, f)
            i = 0
            for k, c in cs.items():
                levels.append((x + i, y + 1, (k, c)))
                i += int(c[0] * scale + 0.5)

        return True
