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

from austin_tui.widgets import Container


class Window(Container):
    """Window container.

    This is, essentially, a wrapper around the ``curses.win`` object.
    """

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.win = self

    def resize(self) -> bool:
        """Resize the window.

        This is effectively resizing just the child widget, as the window itself
        is just a logical container.
        """
        super().resize()

        (child,) = self._children
        child.height, child.width = self.get_size()

        if child.resize():
            self.refresh()
            return True

        return False

    def show(self) -> None:
        """Show the window on screen."""
        if self._win is not None:
            return

        self._win = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self._win.keypad(True)
        try:
            curses.start_color()
        except Exception:
            pass

        curses.use_default_colors()
        curses.curs_set(False)

        self._win.clear()
        self._win.timeout(0)  # non-blocking for async I/O
        self._win.nodelay(True)

        self.height, self.width = self.get_size()

        super().show()

    def hide(self) -> None:
        """Hide the window.

        Also restore the terminal to a sane status.
        """
        if self._win is None:
            return

        self._win.keypad(False)
        curses.echo()
        curses.nocbreak()
        curses.endwin()

        self._win = None

    def get_size(self) -> Tuple[int, int]:
        """Get the window size.

        As per curses convention this returns the tuple (_height_, _width_).
        """
        return self._win.getmaxyx()

    def get_win(self) -> Optional["curses._CursesWindow"]:
        """Get the underlying curses window.

        Use with care.
        """
        return self._win

    def is_visible(self) -> bool:
        """Whether the window is visible."""
        return self._win is not None
