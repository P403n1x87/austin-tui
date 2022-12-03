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
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union


class Point(complex):
    """A point object for easy vector and symplectic operations."""

    def along(self, other: complex) -> "Point":
        """Project the point along the given complex number."""
        return Point((other.conjugate() * self).real * other / abs(other) ** 2)  # type: ignore[call-overload]

    @property
    def x(self) -> int:
        """The x coordinate of the point."""
        return int(self.real)

    @property
    def y(self) -> int:
        """The y coordinate of the point."""
        return int(self.imag)

    @property
    def to_tuple(self) -> Tuple[int, int]:
        """Convert to the (x, y) pair."""
        return (int(self.real), int(self.imag))


class Rect:
    """A rectangle object.

    Represent the rectangular area that a widget is allowed to occupy. This is
    described by a position point and a size point.
    """

    def __init__(self, pos: Union[Point, complex], size: Union[Point, complex]) -> None:
        self.pos = Point(pos)  # type: ignore[call-overload]
        self.size = Point(size)  # type: ignore[call-overload]

    def __eq__(self, other: object) -> bool:
        """Recangle object equality check."""
        if not isinstance(other, Rect):
            raise NotImplementedError()

        return self.pos == other.pos and self.size == other.size

    def __repr__(self) -> str:
        """The rectangle object representation."""
        return f"Rect(pos={self.pos}, size={self.size})"


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
        self._width = int(width or 0)
        self._height = int(height or 0)

        self.pos = Point(self.x, self.y)
        self.size = Point(self.width, self.height)

    @property
    def width(self) -> int:
        """The widget width."""
        return self._width

    @property
    def height(self) -> int:
        """The widget height."""
        return self._height

    @property
    def expand(self) -> Point:
        """The expand directions."""
        return Point(not self.width, not self.height)

    @property
    def rect(self) -> Rect:
        """The widget rectangular area."""
        return Rect(self.pos, self.size)

    @rect.setter
    def rect(self, rect: Rect) -> None:
        self.pos = rect.pos
        self.size = rect.size

    def __repr__(self) -> str:
        """Widget textual representation."""
        return f"{self.__class__.__name__}({self.name})"

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

    def resize(self, rect: Rect) -> bool:
        """Resize the widget.

        This is supposed to change the geometric attribute of the widgets only.
        If a re-draw is required, because any of the widget's attributes have
        changed, an explicit call to draw must be made.

        The optional ``rect`` argument can be used to define the bounding
        rectangle within which the resize is allowed to take place. This is
        normally passed by container widgets to their children to constraint
        their allowed area.

        This method should return ``True`` if a refresh of the screen is needed.
        """
        return False


class BaseContainer(Widget):
    """Base Container widget.

    A base container widget to implement container data structure for child
    widgets.
    """

    def __init__(self, name: str) -> None:
        self._children: List[Widget] = []
        self._children_map: Dict[str, int] = {}
        super().__init__(name)

    def __getattr__(self, name: str) -> Widget:
        """Convenience accessor to child widgets."""
        return self.get_child(name)

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
            ) from None


class Container(BaseContainer):
    """Container widget.

    A container widget is just a logical widget. Therefore it shouldn't draw
    anything on the screen, but delegate the operation to its children.
    """

    def show(self) -> None:
        """Show the children."""
        for child in self._children:
            child.show()

    def hide(self) -> None:
        """Hide the container."""
        for child in self._children:
            child.hide()

    def draw(self) -> bool:
        """Draw the children."""
        refresh = False
        for child in self._children:
            refresh |= child.draw()
        return refresh

    def refresh(self) -> None:
        """Refresh child widgets."""
        super().refresh()

        for child in self._children:
            child.refresh()
