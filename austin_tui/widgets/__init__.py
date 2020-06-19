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


class ContainerError(Exception):
    pass


class Widget:
    def __init__(self, name, width=0, height=0):
        self.win = None
        self.parent = None
        self.view = None

        self.name = name

        # geometry
        self.x = 0
        self.y = 0
        self.width = int(width or 0)
        self.height = int(height or 0)

        self._expand = [not width, not height]

    def refresh(self):
        self.win.refresh()

    def show(self):
        pass

    def hide(self):
        pass

    def draw(self):
        return False

    def resize(self):
        return False


class Container(Widget):
    def __init__(self, name):
        super().__init__(name)
        self._children = []
        self._children_map = {}

    def __getattr__(self, name):
        return self.get_child(name)

    def show(self):
        for child in self._children:
            child.show()

    def draw(self):
        refresh = False
        for child in self._children:
            refresh |= child.draw()
        return refresh

    def add_child(self, child):
        if child.name in self._children_map:
            raise RuntimeError(
                f"Widget {self.name} already has a child with name {child.name}."
            )

        child.parent = self
        child.win = self.win

        self._children_map[child.name] = len(self._children)
        self._children.append(child)

    def get_child(self, name):
        try:
            return self._children[self._children_map[name]]
        except KeyError:
            raise ContainerError(
                f"Widget {self.name} does not contain the child widget {name}"
            )
