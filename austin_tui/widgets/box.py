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

from austin_tui.widgets import Container, Widget


_COORDS = ("x", "y")
_SIZES = ("width", "height")


class Box(Container):
    """A flex box widget.

    The ``flow`` is either ``h``orizontal or ``v``ertical.
    """

    def __init__(self, name: str, flow: str) -> None:
        super().__init__(name)

        if flow[0] not in ["v", "h"]:
            raise ValueError(
                f"Invalid value '{flow}' for attribute 'flow' of widget '{type(self)}'"
            )

        self.flow = {"h": 0, "v": 1}[flow[0]]

        self._expand[self.flow] = False
        self._expand[1 - self.flow] = False

    def add_child(self, child: Widget) -> None:
        """Add child to the box."""
        super().add_child(child)

        rsize = _SIZES[self.flow]
        fsize = _SIZES[1 - self.flow]

        rcoord = _COORDS[self.flow]

        setattr(child, rcoord, getattr(self, rsize))

        setattr(self, rsize, getattr(self, rsize) + getattr(child, rsize))
        setattr(self, fsize, max(getattr(self, fsize), getattr(child, fsize)))

        for _ in range(2):
            self._expand[_] |= child._expand[_]

    def resize(self) -> bool:
        """Resize the box."""
        refresh = super().resize()

        # fixed
        fsize = _SIZES[1 - self.flow]
        fcoord = _COORDS[1 - self.flow]
        # running
        rsize = _SIZES[self.flow]
        rcoord = _COORDS[self.flow]

        touched = set()

        def _set_property(obj: Widget, prop: str, value: Any) -> None:
            old_val = getattr(obj, prop)
            if old_val != value:
                setattr(obj, prop, value)
                touched.add(obj.name)

        # set the fixed size and coordinate straight away
        for child in self._children:
            _set_property(child, fsize, getattr(self, fsize))
            _set_property(child, fcoord, getattr(self, fcoord))

        # compute the height of expanding widgets
        dimensions = [
            0 if child._expand[self.flow] else getattr(child, rsize)
            for child in self._children
        ]
        allocated_dim = sum(dimensions)
        remaining_dim = getattr(self, rsize) - allocated_dim
        n_variable = sum([1 for child in self._children if child._expand[self.flow]])

        if n_variable:
            variable_dimensions = [int(remaining_dim / n_variable)] * n_variable
            for i in range(remaining_dim % n_variable):
                variable_dimensions[i] += 1

        # place and resize children
        pos = getattr(self, rcoord)
        for child in self._children:
            _set_property(child, rcoord, pos)
            if child._expand[self.flow]:
                _set_property(child, rsize, variable_dimensions.pop(0))

            if child.name in touched:
                refresh |= child.resize()

            pos += getattr(child, rsize)

        for name in touched:
            child = self._children[self._children_map[name]]
            refresh |= child.draw()

        return refresh
