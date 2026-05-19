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

import asyncio
import sys

from austin.errors import AustinError

from austin_tui.controller import AustinTUIController


class AustinTUI:
    """Austin TUI."""

    def __init__(self) -> None:
        super().__init__()

        self._controller = AustinTUIController()

        self._exception = None

    def run(self) -> None:
        """Run the TUI."""
        try:
            asyncio.run(self._controller.start(sys.argv[1:]))
        except KeyboardInterrupt:
            self._controller.shutdown()
        except asyncio.CancelledError:
            self._controller.shutdown()
        except Exception:
            self._controller.shutdown()
            raise


def main() -> None:
    """Main function."""
    if sys.platform == "win32":
        asyncio.set_event_loop(asyncio.ProactorEventLoop())

    tui = AustinTUI()

    try:
        tui.run()
    except AustinError as e:
        print(
            "❌ Austin failed to start:                                                    \n"
            f"\n  ❯ {e}\n\n"
            "Please make sure that the Austin binary is available from the PATH environment\n"
            "variable and that the command line arguments that you have provided are correct.",
            file=sys.stderr,
        )
        import os

        if os.environ.get("AUSTIN_DEBUG", None) is not None:
            import traceback

            traceback.print_exc()
        exit(-1)

    exit(0)


if __name__ == "__main__":
    main()
