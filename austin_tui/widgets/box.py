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

from typing import List

from austin_tui.widgets import Container
from austin_tui.widgets import Point
from austin_tui.widgets import Rect


class Box(Container):
    """A flex box widget.

    The ``flow`` is either ``h``orizontal or ``v``ertical.
    """

    def __init__(self, name: str, flow: str) -> None:
        if flow[0] not in ["v", "h"]:
            raise ValueError(
                f"Invalid value '{flow}' for attribute 'flow' of widget '{type(self)}'"
            )

        self.flow = {"h": 1, "v": 1j}[flow[0]]

        super().__init__(name)

    def _dims(self, flow: complex) -> List[int]:
        return [
            0
            if child.expand.along(flow)
            else int(abs(Point(child.width, child.height).along(flow)))
            for child in self._children
        ]

    def _dimsum(self, flow: complex) -> int:
        dimensions = self._dims(flow)

        if 0 in dimensions:
            return 0

        return sum(dimensions)

    def _dimmax(self, flow: complex) -> int:
        dimensions = self._dims(flow)

        if not dimensions or 0 in dimensions:
            return 0

        return max(dimensions)

    @property
    def width(self) -> int:
        """The box width."""
        if self.flow == 1:
            return self._dimsum(1)
        return self._dimmax(1)

    @property
    def height(self) -> int:
        """The box height."""
        if self.flow == 1j:
            return self._dimsum(1j)
        return self._dimmax(1j)

    def resize(self, rect: Rect) -> bool:
        """Resize the box."""
        refresh = super().resize(rect)

        if self.rect == rect:
            return False

        self.rect = rect

        # compute the height of expanding widgets
        dimensions = [
            0
            if child.expand.along(self.flow)
            else abs(Point(child.width, child.height).along(self.flow))
            for child in self._children
        ]
        nvar = sum(_ == 0 for _ in dimensions)

        allocated_dim = sum(dimensions)
        remaining_dim = int(abs(self.size.along(self.flow)) - allocated_dim)

        if nvar:
            var_dim, res_dim = divmod(remaining_dim, nvar)
        else:
            var_dim, res_dim = 0, remaining_dim

        # place and resize children
        perp = Point(self.size.along(1j * self.flow.conjugate()))  # type: ignore[call-overload]
        pos = self.pos
        for child, dim in zip(self._children, dimensions):
            size = perp
            if not dim:
                if res_dim:
                    e = 1
                    res_dim -= 1
                else:
                    e = 0
                size = Point(size + (var_dim + e) * self.flow)
            else:
                size = Point(size + dim * self.flow)

            refresh |= child.resize(Rect(pos, size))

            pos = Point(pos + size.along(self.flow))

        return refresh
