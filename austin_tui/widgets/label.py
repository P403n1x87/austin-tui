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
from collections import deque
from enum import Enum

from austin_tui.view.palette import Color
from austin_tui.widgets import Widget


class TextAlign(Enum):
    LEFT = ""
    RIGHT = ">"
    CENTER = "^"


def ell(text, length, sep=".."):
    if len(text) <= length:
        return text

    if length <= len(sep):
        return sep[:length]

    m = length >> 1
    n = length - m
    a = len(sep) >> 1
    b = len(sep) - a

    return text[: n - b - 1] + sep + text[-m + a - 1 :]


class Label(Widget):
    def __init__(
        self,
        y,
        x,
        width=None,
        text="",
        align=TextAlign.LEFT,
        color=0,
        reverse=False,
        bold=False,
        ellipsize=True,
    ):
        super().__init__()

        self.x = x
        self.y = y
        self.color = curses.color_pair(color)
        self.reverse = reverse and curses.A_REVERSE or 0
        self.bold = bold and curses.A_BOLD or 0
        self.text = text
        self.ellipsize = ellipsize
        self.width = width
        self.align = align

        self.scr = None

    def set_text(self, text):
        self.text = text
        # self.refresh()

    def set_color(self, color: Color):
        self.color = curses.color_pair(color)

    def set_bold(self, bold=True):
        self.bold = bold and curses.A_BOLD or 0

    def get_text(self):
        return self.text

    @property
    def attr(self):
        return self.color | self.bold | self.reverse

    def refresh(self):
        if self.scr is None:
            self.scr = self.get_toplevel().get_screen()

        attr = self.attr
        width = self.width or (max(0, self.scr.getmaxyx()[1] - self.x - 1))
        format = "{:" + f"{self.align.value}{width}" + "}"

        if isinstance(self.text, list):
            for i, line in enumerate(self.text):
                text = format.format(line or "")
                if self.ellipsize:
                    text = ell(text, width)
                self.scr.addstr(self.y + i, self.x, text, attr)
        else:
            text = format.format(self.text or "")
            if self.ellipsize:
                text = ell(text, width)
            self.scr.addstr(self.y, self.x, format.format(text or ""), attr)


class TaggedLabel(Label):
    def __init__(
        self,
        y,
        x,
        width=None,
        text="",
        tag={},
        align=TextAlign.LEFT,
        color=0,
        reverse=False,
        bold=False,
        ellipsize=True,
    ):
        super().__init__(y, x, width, text, align, color, reverse, bold, ellipsize)
        self.orig_x, self.orig_y = x, y

        self.add_child("tag", Label(y, x, **tag))

    def refresh(self):
        tag = self.get_child("tag")
        tag.refresh()
        self.x = self.orig_x + len(tag.get_text()) + 1
        super().refresh()
        self.scr.addstr(self.y, self.x - 1, " ")


class Line(Label):
    def __init__(self, y, x, text="", color=0, reverse=False, bold=False):
        super().__init__(
            y, x, text=text, color=color, reverse=reverse, bold=bold, ellipsize=False
        )

    def refresh(self):
        super().refresh()

        self.scr.chgat(self.attr)


class BarPlot(Label):

    STEPS = [" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]

    @staticmethod
    def bar_icon(i):
        i = max(0, min(i, 1))
        return BarPlot.STEPS[int(i * (len(BarPlot.STEPS) - 1))]

    def __init__(self, y, x, width=8, scale=None, init=None, color=0):
        super().__init__(y, x, width=8, color=color, ellipsize=False)

        self._values = deque([init] * width if init is not None else [], maxlen=width)
        self.scale = scale or 0
        self.auto = not scale

    def push(self, value):
        self._values.append(value)
        if self.auto:
            self.scale = max(self._values)

        self.plot()

        return value

    def plot(self):
        self.set_text(
            "".join(
                BarPlot.bar_icon(v / self.scale if self.scale else v)
                for v in self._values
            )
        )
