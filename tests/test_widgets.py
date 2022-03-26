from typing import Generator

import pytest

from austin_tui.widgets import Point
from austin_tui.widgets import Rect
from austin_tui.widgets.box import Box
from austin_tui.widgets.label import Label
from austin_tui.widgets.scroll import ScrollView
from austin_tui.widgets.table import Table
from austin_tui.widgets.window import Window
from tests.mcurses import MWindow


class MockWindow(Window):
    def get_size(self) -> Point:
        return Point(80, 32)

    def resize(self):
        super().resize(Rect(0, self.get_size()))


@pytest.fixture
def win() -> Generator[Window, None, None]:
    win = MockWindow("test")
    # win._win = MWindow(80, 32)

    yield win


def test_window_resize(win):
    win.resize()

    assert win.rect == Rect(Point(0), Point(80 + 32j))


@pytest.mark.parametrize(
    "w, h, size",
    [
        (10, 4, Point(10 + 4j)),
        (0, 4, Point(80 + 4j)),
        (10, 0, Point(10 + 32j)),
        (0, 0, Point(80 + 32j)),
    ],
)
def test_label_resize(win, w, h, size):
    label = Label("test-label", w, h, "some text")

    win.add_child(label)

    win.resize()

    assert win.rect == Rect(Point(0), Point(80 + 32j))
    assert label.rect == Rect(Point(0), size)


def test_box_resize(win):
    box = Box("test-box", "v")
    win.add_child(box)

    label1 = Label("label1", 0, 0)
    label2 = Label("label2", 0, 5)
    label3 = Label("label3", 10, 0)
    label4 = Label("label4", 20, 6)

    box.add_child(label1)
    box.add_child(label2)
    box.add_child(label3)
    box.add_child(label4)

    win.resize()

    assert box.rect == win.rect

    assert label1.rect == Rect(Point(0), Point(80 + 11j))
    assert label2.rect == Rect(Point(11j), Point(80 + 5j))
    assert label3.rect == Rect(Point(16j), Point(10 + 10j))
    assert label4.rect == Rect(Point(26j), Point(20 + 6j))


def test_nested_box(win):
    hbox = Box("hbox", "h")
    vbox = Box("vbox", "v")

    win.add_child(vbox)

    header = Label("header", height=2)
    footer = Label("footer", height=1)
    sidepane = Label("lx", width=24, height=0)
    content = Label("content", height=0)

    hbox.add_child(sidepane)
    hbox.add_child(content)

    vbox.add_child(header)
    vbox.add_child(hbox)
    vbox.add_child(footer)

    win.resize()

    assert vbox.rect == win.rect == Rect(0, 80 + 32j)
    assert hbox.rect == Rect(2j, 80 + 29j)
    assert header.rect == Rect(0, 80 + 2j)
    assert footer.rect == Rect(31j, 80 + 1j)
    assert sidepane.rect == Rect(2j, 24 + 29j)
    assert content.rect == Rect(24 + 2j, 56 + 29j)


def test_nested_box_complex_header(win):
    """
    / VBOX /
    +------------+------------+
    | LOGO 6 x 3 | INFO 0 x 4 | <- HBOX
    +------------+------------+
    | MBOX                    |
    +-------------------------+
    """
    hbox = Box("hbox", "h")
    vbox = Box("vbox", "v")
    mbox = Box("vbox", "v")

    win.add_child(vbox)
    vbox.add_child(hbox)
    vbox.add_child(mbox)

    logo = Label("hello", width=6, height=3)
    info = Label("info", height=4)

    hbox.add_child(logo)
    hbox.add_child(info)

    win.resize()

    assert vbox.rect == win.rect
    assert hbox.rect == Rect(0, 80 + 4j)
    assert logo.rect == Rect(0, 6 + 3j)
    assert info.rect == Rect(6, 74 + 4j)
    assert mbox.rect == Rect(4j, 80 + 28j)


def test_scroll_view(win):
    scroll = ScrollView("scroll-test")
    win.add_child(scroll)

    label = Label("label", height=120)
    scroll.add_child(label)

    win.resize()

    assert scroll.rect == win.rect
    assert scroll.get_view_size() == label.rect.size == Point(79 + 120j)


def test_table(win):
    scroll = ScrollView("scroll-test")
    win.add_child(scroll)
    scroll._win = win._win

    table = Table("testtable", 1)
    scroll.add_child(table)

    table.set_data([[None]] * 3)

    win.resize()

    assert scroll.rect == win.rect
    assert table.rect.pos == scroll.rect.pos
    assert table.rect.size == Point(scroll.rect.size.x - 1, 3)

    table.set_data([[None]] * 70)

    win.resize()

    assert table.rect.pos == scroll.rect.pos
    assert table.rect.size.x == scroll.rect.size.x - 1
    assert table.rect.size.y == 70
