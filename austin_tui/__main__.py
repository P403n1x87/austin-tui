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
from typing import Optional

from austin.aio import AsyncAustin
from austin.cli import AustinArgumentParser
from austin.cli import AustinCommandLineError
from austin.errors import AustinError
from austin.events import AustinMetadata
from austin.events import AustinSample
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
        super().__init__(name="austin-tui", full=False)

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

        self._controller = AustinTUIController()
        self._view = self._controller.view

        self._view.callback = self.on_view_event

        self._global_stats: Optional[str] = None

        self._exception = None
        self._austin_terminated = False

    async def on_sample(self, sample: AustinSample) -> None:
        """Austin sample received callback."""
        self._controller.model.austin.update(sample)

    async def on_metadata(self, metadata: AustinMetadata) -> None:
        if metadata.name == "mode":
            self._view.set_mode(metadata.value)
        elif metadata.name == "python":
            self._view.set_python(metadata.value)
        else:
            self._controller.model.austin.set_metadata(self._meta)

    async def on_terminate(self) -> None:
        """Austin terminate callback."""
        self._austin_terminated = True

        self._global_stats = None
        await self._controller.stop()

        self._view.stop()

    def on_view_event(self, event: AustinView.Event, data: Any = None) -> None:
        """View events handler."""

        def _unhandled(_: Any) -> None:
            raise RuntimeError(f"Unhandled view event: {event}")

        {
            AustinView.Event.QUIT: self.on_shutdown,
            AustinView.Event.EXCEPTION: self.on_exception,
        }.get(event, _unhandled)(data)  # type: ignore[operator]

    async def start(self, args: AustinTUIArgumentParser) -> None:
        """Start Austin and catch any exceptions."""
        try:
            await super().start(args)
        except Exception:
            self.shutdown()
            raise

        pargs = self.get_arguments()

        if pargs.pid is not None:
            child_process = Process(pargs.pid)
        else:
            austin_process = Process(self._proc.pid)
            (child_process,) = austin_process.children()
        command = child_process.cmdline()

        mode = AustinProfileMode.MEMORY if pargs.memory else AustinProfileMode.TIME
        self._view.mode = mode

        """Austin ready callback."""
        self._controller.model.system.set_child_process(child_process)
        self._controller.model.austin.set_metadata(self._meta)
        self._controller.model.austin.set_command_line(command)

        self._controller.start()

        self._view.set_pid(child_process.pid, pargs.children)

    async def _start(self) -> None:
        exc = None
        try:
            await self.start(sys.argv[1:])
            await self.wait()
            await self._view._input_task
        except Exception as e:
            exc = e
            self._view.close()
        except KeyboardInterrupt:
            self._view.close()

        if exc is not None:
            self._view.close()
            raise exc
        if self._exception is not None:
            self._view.close()
            raise self._exception

    def run(self) -> None:
        """Run the TUI."""
        try:
            asyncio.run(self._start())
        except KeyboardInterrupt:
            try:
                self.terminate()
            except AustinError:
                pass
        except asyncio.CancelledError:
            pass

    def shutdown(self) -> None:
        """Shutdown the TUI."""
        try:
            self.terminate()
        except AustinError:
            pass
        self._view.close()

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
            "variable and that the command line arguments that you have provided are correct.",
            file=sys.stderr,
        )
        exit(-1)

    exit(0)


if __name__ == "__main__":
    main()
