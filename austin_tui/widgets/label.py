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
from typing import Optional

from austin_tui.widgets import Point
from austin_tui.widgets import Rect
from austin_tui.widgets import Widget
from austin_tui.widgets.markup import AttrString


class TextAlign(Enum):
    """Text alignment."""

    LEFT = ""
    RIGHT = ">"
    CENTER = "^"


def ell(text: str, length: int, sep: str = "..") -> str:
    """Ellipsize a string to a given length using the given separator."""
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
    """Label widget."""

    def __init__(
        self,
        name: str,
        width: int = 0,
        height: int = 1,
        text: Any = "",
        align: Any = TextAlign.LEFT,
        color: str = "default",
        reverse: bool = False,
        bold: bool = False,
        ellipsize: bool = True,
    ) -> None:
        super().__init__(name, width, height)

        self.color = color
        self.reverse = reverse
        self.bold = bold
        self.text = text
        self.ellipsize = ellipsize
        self.align = (
            align if isinstance(align, TextAlign) else getattr(TextAlign, align.upper())
        )

    def set_text(self, text: Any) -> bool:
        """Set the label text."""
        if isinstance(text, AttrString) and self.text is not text:
            self.text = text
            return self.draw()

        new_text = str(text)
        if new_text != self.text:
            self.text = new_text
            return self.draw()

        return False

    def set_color(self, color: str) -> bool:
        """Set the label color."""
        if color != self.color:
            self.color = color
            return self.draw()

        return False

    def set_bold(self, bold: bool = True) -> bool:
        """Set the label appearance to bold."""
        if bold != self.bold:
            self.bold = bold
            return self.draw()

        return False

    @property
    def attr(self) -> int:
        """The label attributes."""
        try:
            return (
                self.view
                and curses.color_pair(self.view.palette.get_color(self.color))
                or 0
                | (self.bold and curses.A_BOLD or 0)
                | (self.reverse and curses.A_REVERSE or 0)
            )
        except curses.error:
            return 0

    def resize(self, rect: Optional[Rect] = None) -> bool:
        """Resize logic for the label object."""
        width = min(self.width, rect.size.real) or rect.size.real
        height = min(self.height, rect.size.imag) or rect.size.imag
        new_rect = Rect(rect.pos, Point(width, height))
        if self.rect == new_rect:
            return False

        self.rect = new_rect

        self.draw()

        return True

    def draw(self) -> bool:
        """Draw the label."""
        if not self.win:
            return False

        win = self.win.get_win()
        if not win:
            return False

        width = self.size.x
        if not width:
            return False

        if isinstance(self.text, AttrString):
            try:
                win.addstr(self.pos.y, self.pos.x, " " * width, self.attr)
            except curses.error:
                pass
            x = self.pos.x
            if self.align == TextAlign.RIGHT and len(self.text) < width:
                x += width - len(self.text)
            elif self.align == TextAlign.CENTER and len(self.text) < width:
                x += (width - len(self.text)) >> 1
            return self.text.write(win, self.pos.y, x, width) > 0

        attr = self.attr
        format = "{:" + f"{self.align.value}{max(0, width)}" + "}"

        for i, line in enumerate(self.text.split(r"\n")):
            if i >= self.size.y:
                break
            try:
                text = format.format(line or "")
            except ValueError:
                text = ""
            if self.ellipsize:
                text = ell(text, width)
            try:
                win.addstr(self.pos.y + i, self.pos.x, text, attr)
            except curses.error:
                # Curses cannot write at the bottom right corner of the screen
                # so we ignore this error. Be aware that this might be
                # swallowing actual errors.
                pass
        else:
            return False

        return True

    def hide(self) -> None:
        """Hide the label."""
        win = self.win.get_win()
        if not win:
            return

        width = self.size.x
        if not width:
            return

        try:
            win.addstr(self.pos.y, self.pos.x, " " * width, 0)
        except curses.error:
            pass


class Line(Label):
    """A line that spans the width of its container."""

    def __init__(
        self,
        name: str,
        text: str = "",
        color: str = "default",
        reverse: bool = False,
        bold: bool = False,
    ) -> None:
        super().__init__(
            name=name,
            text=text,
            color=color,
            reverse=reverse,
            bold=bold,
            ellipsize=False,
        )


class ToggleLabel(Label):
    """Toggle label.

    A convenience label that can toggle between two different colors.
    """

    def __init__(
        self,
        name: str,
        width: int = 0,
        height: int = 1,
        text: str = "",
        align: TextAlign = TextAlign.LEFT,
        on: str = "default",
        off: str = "default",
        state: str = "0",
        reverse: bool = False,
        bold: bool = False,
        ellipsize: bool = True,
    ) -> None:
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

    @property
    def state(self) -> bool:
        """Get the toggle state."""
        return bool(self._state)

    def toggle(self) -> bool:
        """Toggle the color."""
        self._state = 1 - self._state
        return self.set_color(self._colors[self._state])


class BarPlot(Label):
    """A bar plot widget.

    If a ``scale`` is given, it is used to scale the values. Otherwise
    autoscaling is performed, which can also be enforced with the ``auto``
    argument. The plot can be initialised with an initial value via the ``init``
    argument.
    """

    STEPS = [" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]

    @staticmethod
    def _bar_icon(i: float) -> str:
        i = max(0, min(i, 1))
        return BarPlot.STEPS[int(i * (len(BarPlot.STEPS) - 1))]

    def __init__(
        self,
        name: str,
        width: int = 8,
        scale: Optional[int] = None,
        init: Optional[int] = None,
        color: str = "default",
    ) -> None:
        super().__init__(name, width=8, color=color, ellipsize=False)

        self._values = deque(
            [int(init)] * width if init is not None else [], maxlen=width
        )
        self.scale = int(scale or 0)
        self.auto = not scale

    def _plot(self) -> bool:
        return self.set_text(
            "".join(
                BarPlot._bar_icon(v / self.scale if self.scale else v)
                for v in self._values
            )
        )

    def push(self, value: int) -> bool:
        """Push a new value to the plot."""
        self._values.append(value)
        if self.auto:
            self.scale = max(self._values)

        return self._plot()
