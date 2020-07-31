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


from abc import ABC
from enum import Enum
from typing import Any

from austin_tui.models import Model
from austin_tui.view import View


class Event(Enum):
    """Base controller event.

    Elements should all be declared as strings representing the name of the
    event. The corresponding controller class should then implement a method
    with the same name and with signature ``Optional[Any] -> Any``
    """

    pass


class Controller(ABC):
    """Base controller.

    Any subclass must implement an event handler as instance method for each
    event declared in the corresponding ``Event`` enumeration. The expected
    signature is ``Optional[Any] -> Any``, but oftentimes the return value is a
    ``bool`` indicating whether a refresh of the UI is required or not.
    """

    __model__ = Model

    def __init__(self, view: View) -> None:
        self.view = view
        self.model = self.__model__()

    def push(self, event: Event, data: Any = None) -> Any:
        """Push an event to the controller.

        Optional data can be passed to the event handler via the ``data``
        argument.
        """
        return getattr(self, event.value)(data)
