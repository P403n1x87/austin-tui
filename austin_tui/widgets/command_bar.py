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

from austin_tui.widgets import Widget


class CommandBar(Widget):
    def __init__(self, commands):
        super().__init__()

        self._cmds = commands
        self.scr = None
        self.h = 0

    def refresh(self):
        if not self.scr:
            self.scr = self.get_toplevel().get_screen()

        h, w = self.scr.getmaxyx()
        x, y = 1, h - 1

        for label, key in self._cmds.items():
            if x + len(key) + len(label) + 3 > w:
                self.scr.clrtoeol()
                self.scr.chgat(0)
                x = 1
                y -= 1

            try:
                self.scr.addstr(y, x, key, curses.A_REVERSE)
                x += len(key)
                self.scr.addstr(y, x, " " + label + "  ")
                x += len(label) + 2
            except curses.error:
                pass

        self.h = h - y

        self.scr.chgat(0)
        self.scr.clrtoeol()

    def get_height(self):
        return self.h
