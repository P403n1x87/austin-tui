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
from typing import Optional, Tuple

from austin_tui.widgets import Container, Widget


class ScrollView(Container):
    """Scroll view container widget.

    This is essentially a wrapper around the curses pad object. The drawing of
    a scroll bar is taken care of.
    """

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self._win: Optional[curses._CursesWindow] = None

        self.win = self

        # curses pad geometry
        self.curr_y = 0
        self.curr_x = 0
        self.w = 1
        self.h = 1

    def get_win(self) -> Optional["curses._CursesWindow"]:
        """Get the underlying curses pad.

        Use with care.
        """
        return self._win

    def add_child(self, child: Widget) -> None:
        """Add the scroll view child widget."""
        child.parent = self
        child.win = self

        self._children_map = {child.name: 0}
        self._children = [child]

    def show(self) -> None:
        """Show the scroll view."""
        super().show()

        if self._win is not None:
            return

        self._win = curses.newpad(1, 1)
        self._win.scrollok(True)
        self._win.keypad(True)
        self._win.timeout(0)
        self._win.nodelay(True)

    def get_inner_size(self) -> Tuple[int, int]:
        """Get the scroll view inner size.

        As per curses convention, the returned value is (_height_, _width_).
        """
        return self.height, self.width - 1

    def scroll_down(self, lines: int = 1) -> None:
        """Scroll the view down."""
        h = self.height

        if self.curr_y + h == self.h:
            return

        self.curr_y += lines
        if self.curr_y + h > self.h:
            self.curr_y = self.h - h

        self._draw_scroll_bar()

    def scroll_up(self, lines: int = 1) -> None:
        """Scroll the view up."""
        if self.curr_y == 0:
            return

        self.curr_y -= lines
        if self.curr_y < 0:
            self.curr_y = 0

        self._draw_scroll_bar()

    def get_view_size(self) -> Tuple[int, int]:
        """Get the scroll view size.

        As per curses convention, the returned value is (_height_, _width_).
        """
        return self.h, self.w

    def set_view_size(self, h: int, w: int) -> None:
        """Set the view size.

        This is the outer size of the view. The actual inner space is computed
        automatically to allow extra space for the scroll bar.
        """
        if self._win is None:
            return

        oh, ow = self.h, self.w
        self.h, self.w = max(h, self.height), max(w, self.width - 1)

        if self.h != oh or self.w != ow:
            self._win.resize(self.h, self.w)  # Scroll bar

    def _draw_scroll_bar(self) -> None:
        if not self._win:
            return

        y0, x0 = self.y, self.x
        h, w = self.height, self.width

        x = x0 + w - 1

        self.parent.win._win.vline(y0, x, curses.ACS_VLINE, h)

        bar_h = min(int(h * h / self.h) + 1, h)
        if bar_h != h:
            bar_y = int(self.curr_y / self.h * h)
            self.parent.win._win.vline(y0 + bar_y, x, curses.ACS_CKBOARD, bar_h)

    def resize(self) -> bool:
        """Resize the scroll view."""
        refresh = super().resize()

        self.set_view_size(self.h, self.w)

        (child,) = self._children
        child.width = max(child.width, self.width - 1)
        child.height = max(child.height, self.height)
        if child.resize():
            refresh |= self.draw()
            self.refresh()

        return refresh

    def draw(self) -> bool:
        """Draw the scroll view."""
        if self._win is None:
            return False

        h = self.height

        if self.curr_y + h > self.h:
            self.curr_y = self.h - h

        self._draw_scroll_bar()

        return True

    def refresh(self) -> None:
        """Refresh the scroll view."""
        h, w = self.height, self.width

        if self.curr_y + h > self.h:
            self.curr_y = self.h - h

        y1, x1 = self.y, self.x

        y2, x2 = y1 + h - 1, x1 + w - 1

        self._win.refresh(self.curr_y, self.curr_x, y1, x1, y2, x2)
        for child in self._children:
            child.refresh()
