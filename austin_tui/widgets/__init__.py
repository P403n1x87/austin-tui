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
from typing import Dict, List, Optional


class ContainerError(Exception):
    """Container widget error."""

    pass


class Widget:
    """Base widget class.

    Every widget should have a name, and some width and height requests. By
    default, ``width`` and ``height`` are set to ``0``, meaning that the widget
    is happy to be stretched by a parent container as needed.
    """

    def __init__(self, name: str, width: int = 0, height: int = 0) -> None:
        self._win: Optional[curses._CursesWindow] = None
        self.win: Optional[Widget] = None
        self.parent: Optional[Widget] = None
        self.view = None

        self.name = name

        # geometry
        self.x = 0
        self.y = 0
        self.width = int(width or 0)
        self.height = int(height or 0)

        self._expand = [not width, not height]

    def refresh(self) -> None:
        """Refresh the widget.

        This method should cause the appropriate underlying curses window to be
        refreshed in order to actually draw the changed widgets.
        """
        if self._win:
            self._win.refresh()

    def show(self) -> None:
        """Show the widget.

        This method is used to create the required low-level curses windows and
        to make a first call to ``resize`` to give widgets the initial positions
        and sizes.
        """
        pass

    def hide(self) -> None:
        """Hide the widget.

        If a curses window is no longer needed, this would be the place to
        destroy it and reset the terminal to its original state.
        """
        pass

    def draw(self) -> bool:
        """Draw the widget on screen.

        This method must return ``True`` if a refresh of the screen is required.
        """
        return False

    def resize(self) -> bool:
        """Resize the widget.

        This is supposed to change the geometric attribute of the widgets only.
        If a re-draw is required, because any of the widget's attributes have
        changed, an explicit call to draw must be made.

        This method should return ``True`` if a refresh of the screen is needed.
        """
        return False


class Container(Widget):
    """Container widget.

    A container widget is just a logical widget. Therefore it shouldn't draw
    anything on the screen, but delegate the operation to its children.
    """

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self._children: List[Widget] = []
        self._children_map: Dict[str, int] = {}

    def __getattr__(self, name: str) -> Widget:
        """Convenience accessor to child widgets."""
        return self.get_child(name)

    def show(self) -> None:
        """Show the children."""
        for child in self._children:
            child.show()

    def draw(self) -> bool:
        """Draw the children."""
        refresh = False
        for child in self._children:
            refresh |= child.draw()
        return refresh

    def add_child(self, child: Widget) -> None:
        """Add a child widget."""
        if child.name in self._children_map:
            raise RuntimeError(
                f"Widget {self.name} already has a child with name {child.name}."
            )

        child.parent = self
        child.win = self.win

        self._children_map[child.name] = len(self._children)
        self._children.append(child)

    def get_child(self, name: str) -> Widget:
        """Get a child widget by name."""
        try:
            return self._children[self._children_map[name]]
        except KeyError:
            raise ContainerError(
                f"Widget {self.name} does not contain the child widget {name}"
            )

    def refresh(self) -> None:
        """Refresh child widgets."""
        super().refresh()

        for child in self._children:
            child.refresh()
