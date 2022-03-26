from austin_tui.widgets import Point


def test_point_along():
    assert Point(5 + 4j).along(1) == 5
    assert Point(5 + 4j).along(1j) == 4j
    assert Point(5 + 4j).along(2j) == 4j


def test_point_tuple():
    assert Point(3 + 4j).to_tuple == (3, 4)
    assert Point(3 + 4j).along(1).to_tuple == (3, 0)
    assert Point(3 + 4j).along(1j).to_tuple == (0, 4)


def test_point_perp():
    size = Point(10, 20)
    dir = 1 + 0j
    perp = size.along(1j * dir.conjugate())
    assert perp == Point(20j)

    assert Point(perp + 5 * dir) == Point(5 + 20j)
