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

from abc import ABC, abstractmethod
import curses
from dataclasses import dataclass
from typing import Any, List

from austin_tui.view.palette import Palette
from lxml import etree


def escape(text: str) -> str:
    """Escape angle brackets."""
    return text.replace("<", "&lt;").replace(">", "&gt;")


def _unescape(text: str) -> str:
    """Unescape angle brackets."""
    return text.replace("&lt;", "<").replace("&gt;", ">")


class StringAttr:
    """The string attributes."""

    BOLD = "b"
    REVERSED = "r"


class Writable(ABC):
    """A writable object base class."""

    @abstractmethod
    def write(self, *args: Any, **kwargs: Any) -> None:
        """Write the writable object."""
        ...


@dataclass
class AttrStringChunk(Writable):
    """A chunk of an attribute string.

    A chunk represents a part of a string with certain curses-specific
    attributes, like color.
    """

    text: str
    color: int = 0
    bold: bool = False
    reversed: bool = False

    @property
    def attr(self) -> int:
        """The chunk attributes."""
        attr = 0
        if self.color:
            attr |= curses.color_pair(self.color)
        if self.bold:
            attr |= curses.A_BOLD
        if self.reversed:
            attr |= curses.A_REVERSE
        return attr

    def write(
        self, window: "curses._CursesWindow", y: int, x: int, maxlen: int = None
    ) -> int:
        """Write the chunk on the given curses window.

        The ``maxlen`` argument can be used to cap the string length.
        """
        text = _unescape(self.text)
        text = text[:maxlen] if maxlen is not None else text
        window.addstr(y, x, text, self.attr)
        return len(text)

    def __len__(self) -> int:
        """The actual length of the string."""
        return len(str(self))

    def __str__(self) -> str:
        """The plain underlying string."""
        return _unescape(self.text)


class AttrString(Writable):
    """Attribute string class.

    This is a convenience class for writing strings with chunks having different
    attributes (e.g. color).
    """

    def __init__(self) -> None:
        self._chunks: List[AttrStringChunk] = []

    def append(self, chunk: AttrStringChunk) -> None:
        """Append a chunk."""
        self._chunks.append(chunk)

    def __repr__(self) -> str:
        """A detailed representation of the AttrString object."""
        return f"{type(self).__qualname__}{repr(self._chunks)}"

    def __str__(self) -> str:
        """The plain underlying string."""
        return "".join(str(_) for _ in self._chunks)

    def __len__(self) -> int:
        """The actual string length."""
        return sum(len(_) for _ in self._chunks)

    def write(
        self, window: "curses._CursesWindow", y: int, x: int, maxlen: int = None
    ) -> int:
        """Write the attribute string on the given window.

        The ``maxlen`` argument can be used to cap the string length.
        """
        i = x
        available = maxlen
        n = 0
        for chunk in self._chunks:
            written = chunk.write(window, y, i, available)
            n += written
            if available is not None:
                available -= written
                if available <= 0:
                    break
            i += len(chunk.text)
        return n


def markup(text: str, palette: Palette) -> AttrString:
    """Use XML markup to generate an attribute string."""
    astr = AttrString()

    root = etree.fromstring(f"<amRoot>{text}</amRoot>")

    def add_strings(
        node: etree.Element,
        color: str = "default",
        bold: bool = False,
        reversed: bool = False,
    ) -> None:
        """Recursively parse the tag tree to generare chunks."""
        _color = palette.get_color(color)
        if node.text:
            astr.append(AttrStringChunk(node.text, _color, bold, reversed))

        for e in node:
            if e.tag == StringAttr.BOLD:
                add_strings(e, color=color, bold=True, reversed=reversed)
            elif e.tag == StringAttr.REVERSED:
                add_strings(e, color=color, bold=bold, reversed=True)
            else:
                add_strings(e, color=e.tag, bold=bold, reversed=reversed)
            if e.tail:
                astr.append(AttrStringChunk(e.tail, _color, bold, reversed))

    add_strings(root)

    return astr
