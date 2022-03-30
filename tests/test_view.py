from austin_tui.view import ViewBuilder
from austin_tui.view.austin import AustinView
from austin_tui.widgets import Point
from austin_tui.widgets import Rect
from tests.mcurses import MWindow


def test_austin_view():
    view_builder = ViewBuilder.from_resource("austin_tui.view", "tui.austinui")

    view = view_builder.build()  # type: ignore[assignment]

    root = view.root_widget
    root._win = MWindow(80, 32)
    root.resize(Rect(0, root.get_size()))

    assert view.main.rect == Rect(0, 80 + 32j)
    assert view.main_box.rect == Rect(0, 80 + 32j)
    assert view.info_box.rect == Rect(0, 80 + 4j)

    assert view.dataview_selector.rect == Rect(4j, 80 + 27j)

    view.dataview_selector.select(1)
    root.resize(Rect(0, root.get_size()))

    assert view.dataview_selector.rect == Rect(4j, 80 + 27j)
    assert view.flame_view.rect == Rect(5j, 80 + 26j)
