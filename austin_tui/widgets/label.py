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
from typing import Any

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
        name,
        width=None,
        height=1,
        text="",
        align=TextAlign.LEFT,
        color="default",
        reverse=False,
        bold=False,
        ellipsize=True,
    ):
        super().__init__(name, width, height)

        self.color = color
        self.reverse = reverse
        self.bold = bold
        self.text = text
        self.ellipsize = ellipsize
        self.align = (
            align if isinstance(align, TextAlign) else getattr(TextAlign, align.upper())
        )

    def set_text(self, text: Any) -> None:
        new_text = str(text)
        if new_text != self.text:
            self.text = new_text
            return self.draw()

        return False

    def set_color(self, color: str):
        if color != self.color:
            self.color = color
            return self.draw()

        return False

    def set_bold(self, bold=True):
        if bold != self.bold:
            self.bold = bold and curses.A_BOLD or 0
            return self.draw()

        return False

    @property
    def attr(self):
        return (
            curses.color_pair(self.view.palette.get_color(self.color))
            | (self.bold and curses.A_BOLD or 0)
            | (self.reverse and curses.A_REVERSE or 0)
        )

    def draw(self):
        win = self.win.get_win()
        if not win:
            return False

        width = self.width or (max(0, self.parent.width - self.x - 1))
        if not width:
            return False

        attr = self.attr
        format = "{:" + f"{self.align.value}{width}" + "}"

        for i, line in enumerate(self.text.split(r"\n")):
            if i >= self.height:
                break
            text = format.format(line or "")
            if self.ellipsize:
                text = ell(text, width)
            try:
                win.addstr(self.y + i, self.x, text, attr)
            except curses.error:
                # Curses cannot write at the bottom right corner of the screen
                # so we ignore this error. Be aware that this might be
                # swallowing actual errors.
                pass
        else:
            return False

        return True


class Line(Label):
    def __init__(self, name, text="", color="default", reverse=False, bold=False):
        super().__init__(
            name=name,
            text=text,
            color=color,
            reverse=reverse,
            bold=bold,
            ellipsize=False,
        )

    def refresh(self):
        super().refresh()


class ToggleLabel(Label):
    def __init__(
        self,
        name,
        width=None,
        height=1,
        text="",
        align=TextAlign.LEFT,
        on="default",
        off="default",
        state="0",
        reverse=False,
        bold=False,
        ellipsize=True,
    ):
        self._colors = (off, on)
        self._state = int(state)

        super().__init__(
            name,
            width=width,
            height=height,
            text=text,
            align=align,
            color=self._colors[self._state],
            reverse=reverse,
            bold=bold,
            ellipsize=ellipsize,
        )

    def toggle(self):
        self._state = 1 - self._state
        return self.set_color(self._colors[self._state])


class BarPlot(Label):

    STEPS = [" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]

    @staticmethod
    def bar_icon(i):
        i = max(0, min(i, 1))
        return BarPlot.STEPS[int(i * (len(BarPlot.STEPS) - 1))]

    def __init__(self, name, width=8, scale=None, init=None, color="default"):
        super().__init__(name, width=8, color=color, ellipsize=False)

        self._values = deque(
            [int(init)] * width if init is not None else [], maxlen=width
        )
        self.scale = int(scale or 0)
        self.auto = not scale

    def _plot(self):
        return self.set_text(
            "".join(
                BarPlot.bar_icon(v / self.scale if self.scale else v)
                for v in self._values
            )
        )

    def push(self, value):
        self._values.append(value)
        if self.auto:
            self.scale = max(self._values)

        return self._plot()
