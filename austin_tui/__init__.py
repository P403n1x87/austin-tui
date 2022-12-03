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

import os
import sys
from enum import Enum
from traceback import format_exception


class AustinProfileMode(Enum):
    """Austin profile modes."""

    TIME = "Time"
    MEMORY = "Memory"


if os.environ.get("AUSTIN_TUI_DEBUG"):
    _original_excepthook = sys.excepthook

    def _excepthook(exc_type, exc, tb):
        try:
            os.remove("austin-tui.exc")
        except Exception:
            pass
        with open("austin-tui.exc", "w") as fout:
            fout.writelines(format_exception(exc_type, exc, tb))
        _original_excepthook(exc_type, exc, tb)

    sys.excepthook = _excepthook
