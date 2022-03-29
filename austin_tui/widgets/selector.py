# This file is part of "austin-tui" which is released under GPL.
#
# See file LICENCE or go to http://www.gnu.org/licenses/ for full license
# details.
#
# austin-tui is top-like TUI for Austin.
#
# Copyright (c) 2018-2022 Gabriele N. Tornetta <phoenix1987@gmail.com>.
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

from typing import Optional

from austin_tui.widgets import BaseContainer
from austin_tui.widgets import Rect
from austin_tui.widgets import Widget


class SelectorError(Exception):
    """Generic selector error."""

    pass


class Selector(BaseContainer):
    """Selector widget.

    Allows toggling between a set of widgets to display at a time.
    """

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self._selected = 0

    @property
    def selected(self) -> Optional[Widget]:
        """Get the selected widget."""
        try:
            return self._children[self._selected]
        except IndexError as e:
            raise SelectorError("Invalid selection") from e

    def select(self, index: int) -> None:
        """Select the widget to display."""
        if not (0 <= index < len(self._children)):
            raise SelectorError(f"Invalid selector index: {index}")

        if self._selected != index:
            self.hide()
            self._selected = index
            self.show()
            self.selected.resize(self.rect)
            self.draw()
            self.refresh()

    def show(self) -> None:
        """Show the selected widget."""
        try:
            self.selected.show()
        except SelectorError:
            pass

    def hide(self) -> None:
        """Hide the selected widget."""
        try:
            self.selected.hide()
        except SelectorError:
            pass

    def draw(self) -> bool:
        """Draw the selected widget."""
        try:
            return self.selected.draw()
        except SelectorError:
            return False

    def resize(self, rect: Rect) -> bool:
        """Resize the selected widget."""
        if self.rect == rect:
            return False

        self.rect = rect

        try:
            return self.selected.resize(rect)
        except SelectorError:
            return False

    def refresh(self) -> None:
        """Refresh the selected widget."""
        super().refresh()

        try:
            self.selected.refresh()
        except SelectorError:
            pass
