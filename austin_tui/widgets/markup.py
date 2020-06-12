import curses
from abc import ABC, abstractmethod

from lxml import etree

from austin_tui.view.palette import Color
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
    color: Color = None
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
        text = self.text[:maxlen] if maxlen else self.text
        window.addstr(y, x, _unescape(text), self.attr)
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
            i += len(chunk.text)
        return n


def am(text):
    astr = AttrString()

    root = etree.fromstring(f"<amRoot>{text}</amRoot>")

    def add_strings(node, color=None, bold=False, reversed=False):
        if node.text:
            astr.append(AttrStringChunk(node.text, color, bold, reversed))

        for e in node:
            if e.tag == StringAttr.BOLD:
                add_strings(e, color=color, bold=True, reversed=reversed)
            elif e.tag == StringAttr.REVERSED:
                add_strings(e, color=color, bold=bold, reversed=True)
            else:
                add_strings(
                    e, color=getattr(Color, e.tag.upper()), bold=bold, reversed=reversed
                )
            if e.tail:
                astr.append(AttrStringChunk(e.tail, color, bold, reversed))

    add_strings(root)

    return astr


if __name__ == "__main__":
    a = am("Well <inactive>&lt;hello&gt;</inactive> world<running>!</running>")
    print(repr(a))
    print(a)
    print(len(a))
