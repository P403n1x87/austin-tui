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

from typing import Any, List

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

        h, w = self.height, self.width
        empty = "< Empty >"
        if h < 1 or w < len(empty):
            return True

        win.addstr(h >> 1, (w >> 1) - (len(empty) >> 1), empty)

        return True

    def _draw_row(self, i: int, row: List[Any]) -> None:
        x = 0
        available = self.width
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
                delta = min(text[: available - x], len(text))
            x += delta

    def set_data(self, data: TableData) -> None:
        """Set the table data.

        The format is a list of rows, with each row representing the content of
        each cell.
        """
        if data != self._data:
            h, w = self.parent.height, self.parent.width - 1
            self.height, self.width = h, w
            self.parent.set_view_size(max(len(data), h), w)  # ???

            self._data = data
            self.parent.draw()

    def resize(self) -> bool:
        """Resize the table."""
        self.draw()
        return True

    def draw(self) -> bool:
        """Draw the table."""
        super().draw()

        if not self._data:
            self.parent.set_view_size(self.parent.height, self.parent.width - 1)
            self.width, self.height = self.parent.width - 1, self.parent.height
            return self._show_empty()
        else:
            self.win.get_win().clear()
            i = 0
            for e in self._data:
                self._draw_row(i, e)
                i += 1
            else:
                return False

            return True
