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

from typing import Optional

from austin_tui.model.austin import AustinModel
from austin_tui.model.system import FrozenSystemModel
from austin_tui.model.system import SystemModel


class Model:
    """The application model."""

    __slots__ = ("austin", "system", "frozen_austin", "frozen_system", "frozen")

    _instance: Optional["Model"] = None

    @classmethod
    def get(cls) -> "Model":
        """Get the single model instance."""
        if cls._instance is not None:
            return cls._instance

        model = cls._instance = cls()
        return model

    def __init__(self) -> None:
        self.austin = AustinModel()
        self.system = SystemModel()
        self.frozen_austin: Optional[AustinModel] = None
        self.frozen_system: Optional[FrozenSystemModel] = None
        self.frozen = False

    def toggle_freeze(self) -> None:
        """Toggle the freeze status."""
        if self.frozen:
            self.unfreeze()
        else:
            self.freeze()

    def freeze(self) -> None:
        """Freeze the model."""
        self.frozen_austin = self.austin.freeze()
        self.frozen_system = self.system.freeze()
        self.frozen = True

    def unfreeze(self) -> None:
        """Unfreeze the model."""
        self.frozen_austin = None
        self.frozen_system = None
        self.frozen = False
