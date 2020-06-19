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
from abc import ABC, abstractmethod

from lxml import etree

from dataclasses import dataclass


def escape(text):
    return text.replace("<", "&lt;").replace(">", "&gt;")


def _unescape(text):
    return text.replace("&lt;", "<").replace("&gt;", ">")


class StringAttr:
    BOLD = "b"
    REVERSED = "r"


class Writable(ABC):
    @abstractmethod
    def write(self, *args, **kwargs):
        ...


@dataclass
class AttrStringChunk(Writable):
    text: str
    color: str = "default"
    bold: bool = False
    reversed: bool = False

    @property
    def attr(self):
        attr = 0
        if self.color:
            attr |= curses.color_pair(self.color)
        if self.bold:
            attr |= curses.A_BOLD
        if self.reversed:
            attr |= curses.A_REVERSE
        return attr

    def write(self, window, y, x, maxlen: int = None) -> int:
        text = _unescape(self.text)
        text = text[:maxlen] if maxlen else text
        window.addstr(y, x, text, self.attr)
        return len(text)

    def __len__(self):
        return len(str(self))

    def __str__(self):
        return _unescape(self.text)


class AttrString(Writable):
    def __init__(self):
        self._chunks = []

    def append(self, chunk):
        self._chunks.append(chunk)

    def __repr__(self):
        return f"{type(self).__qualname__}{repr(self._chunks)}"

    def __str__(self):
        return "".join(str(_) for _ in self._chunks)

    def __len__(self):
        return sum(len(_) for _ in self._chunks)

    def write(self, window, y: int, x: int, maxlen: int = None) -> int:
        i = x
        available = maxlen
        n = 0
        for chunk in self._chunks:
            written = chunk.write(window, y, i, available)
            n += written
            available -= written
            if available <= 0:
                break
            i += len(chunk.text)
        return n


def markup(text, palette):
    astr = AttrString()

    root = etree.fromstring(f"<amRoot>{text}</amRoot>")

    def add_strings(node, color="default", bold=False, reversed=False):
        color = palette.get_color(color)
        if node.text:
            astr.append(AttrStringChunk(node.text, color, bold, reversed))

        for e in node:
            if e.tag == StringAttr.BOLD:
                add_strings(e, color=color, bold=True, reversed=reversed)
            elif e.tag == StringAttr.REVERSED:
                add_strings(e, color=color, bold=bold, reversed=True)
            else:
                add_strings(e, color=e.tag, bold=bold, reversed=reversed)
            if e.tail:
                astr.append(AttrStringChunk(e.tail, color, bold, reversed))

    add_strings(root)

    return astr


if __name__ == "__main__":
    a = markup("Well <inactive>&lt;hello&gt;</inactive> world<running>!</running>")
    print(repr(a))
    print(a)
    print(len(a))
