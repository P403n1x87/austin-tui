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


class Widget:
    def __init__(self):
        self.parent = None
        self._children = {}
        self._event_handlers = {"KEY_RESIZE": self.on_resize}

    def __getattr__(self, name):
        try:
            return self._children[name]
        except KeyError:
            raise AttributeError(self, self.parent, name)

    def add_child(self, name, child):
        # if name in self._children:
        #     raise RuntimeError(f"Child {name} already exists.")

        child.parent = self
        self._children[name] = child

    def get_child(self, name):
        return self._children.get(name, None)

    def connect(self, event, handler):
        self._event_handlers[event] = handler

    def dispatch(self, event, *args, **kwargs):
        for _, child in self._children.items():
            if child.dispatch(event, *args, **kwargs):
                return True

        try:
            return self._event_handlers[event](*args, **kwargs)
        except KeyError:
            return False
            # import traceback as tb
            #
            # with open("/tmp/exc", "w") as fout:
            #     fout.write("".join(tb.format_tb(e.__traceback__)))
            # pass

    def on_resize(self):
        self.refresh()
        return False

    def get_toplevel(self):
        toplevel = self
        while toplevel.parent:
            toplevel = toplevel.parent

        return toplevel

    def refresh(self):
        for _, child in self._children.items():
            child.refresh()
