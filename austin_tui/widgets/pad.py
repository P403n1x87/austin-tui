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
from austin_tui.widgets.markup import Writable


class Pad(Widget):
    def __init__(self, position_policy, size_policy):
        super().__init__()

        self.h, self.w = size_policy()

        self._sizep = size_policy
        self._posp = position_policy

        self.pad = curses.newpad(*size_policy())
        self.pad.scrollok(1)
        self.pad.keypad(1)
        self.pad.timeout(0)
        self.pad.nodelay(1)

        self.curr_y = 0
        self.curr_x = 0

        self.connect("KEY_UP", self.on_up)
        self.connect("KEY_DOWN", self.on_down)

    def __getattr__(self, name):
        return getattr(self.pad, name)

    def get_inner_size(self):
        h, w = self._sizep()

        return h, w - 1

    def on_down(self):
        h, _ = self._sizep()
        if self.curr_y + h < self.h:
            self.curr_y += 1
            self.refresh()

    def on_up(self):
        if self.curr_y > 0:
            self.curr_y -= 1
            self.refresh()

    def set_size(self, h, w):
        self.h, self.w = h, w
        self.pad.resize(h, w)  # Scroll bar

    def draw_scroll_bar(self):
        y0, x0 = self._posp()
        h, w = self._sizep()

        x = x0 + w - 1

        scr = self.get_toplevel().get_screen()
        for i in range(h):
            scr.addstr(y0 + i, x, "░")

        bar_h = min(int(h * h / self.h) + 1, h)
        if bar_h != h:
            bar_y = int(self.curr_y / self.h * h)
            for i in range(bar_h):
                scr.addstr(y0 + bar_y + i, x, "▓")

    def refresh(self):
        super().refresh()

        h, w = self._sizep()

        if self.curr_y + h > self.h:
            self.curr_y = 0

        y1, x1 = self._posp()

        y2, x2 = y1 + h - 1, x1 + w - 1

        self.pad.refresh(self.curr_y, self.curr_x, y1, x1, y2, x2)
        self.draw_scroll_bar()


class Table(Pad):
    def __init__(self, position_policy, size_policy, columns, data=[], hook=None):
        super().__init__(position_policy, size_policy)

        self._cols = columns
        self._hook = hook
        self._data = data

    def show_empty(self):
        h, w = self._sizep()
        self.pad.addstr(h >> 1, (w >> 1) - 4, "< Empty >")

    def set_row(self, i, row):
        x = 0
        _, available = self.get_inner_size()
        for j in range(len(self._cols)):
            if available <= 0:
                break
            text = row[j]
            if isinstance(row[j], Writable):
                text.write(self.pad, i, x, available - x)
            else:
                text = self._cols[j].format(row[j])
                self.pad.addstr(i, x, text[: available - x], 0)
            x += len(text)

    def set_data(self, data):
        self._data = data

    def refresh(self):
        data = self._data
        h, w = self._sizep()
        self.set_size(max(len(data), h), w)  # ???

        self.pad.clear()
        if not data:
            self.show_empty()
        else:
            i = 0
            for e in data:
                self.set_row(i, e)
                i += 1

        super().refresh()
