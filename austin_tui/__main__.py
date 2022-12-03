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
from textwrap import wrap
from typing import Any
from typing import List
from typing import Optional

from austin import AustinError
from austin.aio import AsyncAustin
from austin.cli import AustinArgumentParser
from austin.cli import AustinCommandLineError
from psutil import Process

from austin_tui import AustinProfileMode
from austin_tui.controller import AustinTUIController
from austin_tui.view.austin import AustinView


def _print(text: str) -> None:
    for line in wrap(text, 78):
        print(line)


class AustinTUIArgumentParser(AustinArgumentParser):
    """Austin TUI implementation of the Austin argument parser."""

    def __init__(self) -> None:
        super().__init__(
            name="austin-tui", full=False, alt_format=False, exposure=False
        )

    def parse_args(self) -> Any:
        """Parse command line arguments and report any errors."""
        try:
            return super().parse_args()
        except AustinCommandLineError as e:
            reason, *code = e.args
            if reason:
                _print(reason)
            exit(code[0] if code else -1)


class AustinTUI(AsyncAustin):
    """Austin TUI implementation of AsyncAustin."""

    def __init__(self) -> None:
        super().__init__()

        self._args = AustinTUIArgumentParser().parse_args()

        self._controller = AustinTUIController()
        self._view = self._controller.view

        mode = AustinProfileMode.MEMORY if self._args.memory else AustinProfileMode.TIME
        self._view.mode = mode

        self._view.callback = self.on_view_event

        self._global_stats: Optional[str] = None

    def on_sample_received(self, sample: str) -> None:
        """Austin sample received callback."""
        self._controller.model.austin.update(sample)

    def on_ready(
        self, austin_process: Process, child_process: Process, command_line: str
    ) -> None:
        """Austin ready callback."""
        self._controller.model.system.set_child_process(child_process)
        self._controller.model.austin.set_metadata(self._meta)
        self._controller.model.austin.set_command_line(command_line)

        self._controller.start()

        self._view.set_mode(self._meta["mode"])
        self._view.set_pid(child_process.pid, self._args.children)
        self._view.set_python(self.python_version)

    def on_terminate(self, stats: str) -> None:
        """Austin terminate callback."""
        self._global_stats = stats
        self._controller.stop()
        self._controller.update()

        self._view.stop()

    def on_view_event(self, event: AustinView.Event, data: Any = None) -> None:
        """View events handler."""

        def _unhandled(_: Any) -> None:
            raise RuntimeError(f"Unhandled view event: {event}")

        {
            AustinView.Event.QUIT: self.on_shutdown,
            AustinView.Event.EXCEPTION: self.on_exception,
        }.get(event, _unhandled)(
            data
        )  # type: ignore[operator]

    async def start(self, args: List[str]) -> None:
        """Start Austin and catch any exceptions."""
        try:
            print("🏁 Starting the Austin TUI ...", end="", flush=True)
            await super().start(args)
        except Exception:
            self.shutdown()
            raise

    def run(self) -> None:
        """Run the TUI."""
        loop = asyncio.get_event_loop()

        austin = loop.create_task(
            self.start(AustinTUIArgumentParser.to_list(self._args))
        )
        loop.run_forever()

        self._view.close()

        if not austin.done():
            austin.cancel()

        if austin.done():
            austin.result()

    def shutdown(self) -> None:
        """Shutdown the TUI."""
        try:
            self.terminate()
        except AustinError:
            pass

        asyncio.get_event_loop().stop()

    def on_shutdown(self, _: Any = None) -> None:
        """The shutdown view event handler."""
        self.shutdown()

    def on_exception(self, exc: Exception) -> None:
        """The exception view event handler."""
        self.shutdown()
        raise exc


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
            "variable and that the command line arguments that you have provided are correct."
        )
        exit(-1)

    exit(0)


if __name__ == "__main__":
    main()
