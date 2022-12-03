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
from typing import Optional
from typing import Tuple

from austin_tui.widgets import Container
from austin_tui.widgets import Point
from austin_tui.widgets import Rect
from austin_tui.widgets import Widget


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

        try:
            self._win = curses.newpad(self.h, self.w)
        except curses.error:
            return

        self._win.scrollok(True)
        self._win.keypad(True)
        self._win.timeout(0)
        self._win.nodelay(True)

    def hide(self) -> None:
        """Hide the scroll view."""
        super().hide()

        if self._win is not None:
            self._win.clear()
            self.refresh()
            del self._win
            self._win = None

    def get_inner_size(self) -> Point:
        """Get the scroll view inner size.

        As per curses convention, the returned value is (_height_, _width_).
        """
        return Point(self.size - 1)  # type: ignore[call-overload]

    def scroll_down(self, lines: int = 1) -> None:
        """Scroll the view down."""
        h = self.size.y

        if self.curr_y + h == self.h:
            return

        self.curr_y += lines
        if self.curr_y + h > self.h:
            self.curr_y = self.h - h

        self._draw_scroll_bar()

    def scroll_page_down(self) -> None:
        """Scroll one page down."""
        self.scroll_down(self.size.y)

    def scroll_up(self, lines: int = 1) -> None:
        """Scroll the view up."""
        if self.curr_y == 0:
            return

        self.curr_y -= lines
        if self.curr_y < 0:
            self.curr_y = 0

        self._draw_scroll_bar()

    def scroll_page_up(self) -> None:
        """Scroll one page up."""
        self.scroll_up(self.size.y)

    def top(self) -> None:
        """Scroll to the top."""
        self.curr_y = 0
        self._draw_scroll_bar()

    def bottom(self) -> None:
        """Scroll to the bottom."""
        self.curr_y = self.h - self.size.y
        self._draw_scroll_bar()

    def get_view_size(self) -> Point:
        """Get the scroll view size."""
        return Point(self.w, self.h)

    def set_view_size(self, h: int, w: int) -> None:
        """Set the view size.

        This is the outer size of the view. The actual inner space is computed
        automatically to allow extra space for the scroll bar.
        """
        oh, ow = self.h, self.w
        self.h, self.w = max(h, self.size.y), self.size.x - 1

        if self._win and (self.h != oh or self.w != ow):
            self._win.resize(self.h, self.w)  # Scroll bar

    def _draw_scroll_bar(self) -> None:
        if not self._win:
            return

        y0, x0 = self.pos.y, self.pos.x
        h, w = self.size.y, self.size.x

        x = x0 + w - 1

        self.parent.win._win.vline(y0, x, curses.ACS_VLINE, h)

        bar_h = min(int(h * h / self.h) + 1, h)
        if bar_h != h:
            bar_y = int(self.curr_y / self.h * h)
            self.parent.win._win.vline(y0 + bar_y, x, curses.ACS_CKBOARD, bar_h)

    def resize(self, rect: Rect) -> bool:
        """Resize the scroll view."""
        refresh = super().resize(rect)

        self.rect = rect

        if not self._children:
            return False

        (child,) = self._children

        width = self.rect.size.x - 1
        self.set_view_size(child.height, width)

        if child.resize(Rect(0, Point(width, child.height))):
            refresh = self.draw()
            self.refresh()

        self._draw_scroll_bar()

        return refresh

    def draw(self) -> bool:
        """Draw the scroll view."""
        if self._win is None:
            return False

        h = self.size.y

        if self.curr_y + h > self.h:
            self.curr_y = self.h - h

        if self._children:
            (child,) = self._children
            child.draw()

        self._draw_scroll_bar()

        return True

    def refresh(self) -> None:
        """Refresh the scroll view."""
        if not self._win:
            return

        w, h = self.size.to_tuple

        if self.curr_y + h > self.h:
            self.curr_y = self.h - h

        y1, x1 = self.pos.y, self.pos.x

        y2, x2 = y1 + h - 1, x1 + w - 1

        self._win.refresh(self.curr_y, self.curr_x, y1, x1, y2, x2)
        for child in self._children:
            child.refresh()
