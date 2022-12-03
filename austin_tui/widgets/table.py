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
from typing import List

from austin_tui.widgets import Rect
from austin_tui.widgets import Widget
from austin_tui.widgets.markup import Writable


TableData = List[List[Any]]


class Table(Widget):
    """Table widget.

    Requires a number of colums.
    """

    def __init__(self, name: str, columns: Any) -> None:
        super().__init__(name)

        self._cols = int(columns)
        self._data: TableData = []

    def _show_empty(self) -> bool:
        win = self.win.get_win()
        if not win:
            return False

        win.clear()

        return True

    def _draw_row(self, i: int, row: List[Any]) -> None:
        x = 0
        available = self.rect.size.x
        win = self.win.get_win()
        for j in range(self._cols):
            if available <= x:
                break
            text = row[j]
            if isinstance(row[j], Writable):
                delta = text.write(win, i, x, available - x)
            else:
                text = row[j]
                win.addstr(i, x, text[: available - x], 0)
                delta = min(available - x, len(text))
            x += delta

    def set_data(self, data: TableData) -> bool:
        """Set the table data.

        The format is a list of rows, with each row representing the content of
        each cell.
        """
        if data != self._data:
            self._data = data
            self._height = len(data)
            self.parent.resize(self.parent.rect)
            return True

        return False

    def resize(self, rect: Rect) -> bool:
        """Resize the table."""
        if self.rect == rect:
            return False

        self.rect = rect

        self.draw()

        return True

    def draw(self) -> bool:
        """Draw the table."""
        super().draw()

        if not self.win:
            return False

        if not self._data:
            return self._show_empty()
        else:
            win = self.win.get_win()
            if not win:
                return False
            win.clear()
            i = self.pos.y
            for e in self._data:
                self._draw_row(i, e)
                i += 1

        return True
