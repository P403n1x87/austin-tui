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
from typing import Any, List, Optional

from austin import AustinError, AustinTerminated
from austin.aio import AsyncAustin
from austin.cli import AustinArgumentParser, AustinCommandLineError
from austin_tui import catch
from austin_tui.models import AustinModel
from austin_tui.view import ViewBuilder
from austin_tui.view.austin import AustinProfileMode, AustinView
from psutil import Process


try:
    _get_all_tasks = asyncio.all_tasks  # Python 3.7+
except AttributeError:
    _get_all_tasks = asyncio.Task.all_tasks  # Python 3.6 compatibility


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

        self._model = AustinModel()
        self._view: AustinView = ViewBuilder.from_resource(
            "austin_tui.view", "tui.austinui"
        )
        self._view.mode = (
            AustinProfileMode.MEMORY if self._args.memory else AustinProfileMode.TIME
        )
        self._view.callback = self.on_view_event

        self._global_stats: Optional[str] = None

    def on_sample_received(self, sample: str) -> None:
        """Austin sample received callback."""
        self._model.update(sample)

    @catch
    def on_ready(
        self, austin_process: Process, child_process: Process, command_line: str
    ) -> None:
        """Austin ready callback."""
        self._view._system_controller.set_child_process(child_process)

        self._view.open()

        self._view.pid_label.set_text("PPID" if self._args.children else "PID")
        self._view.pid.set_text(child_process.pid)

        self._view.thread_name_label.set_text(
            "{}TID".format("PID:" if self._args.children else "")
        )

        self._view.cmd_line.set_text(command_line)

    def on_terminate(self, stats: str) -> None:
        """Austin terminate callback."""
        self._global_stats = stats
        self._view.stop()

    def on_view_event(self, event: AustinView.Event, data: Any = None) -> None:
        """View events handler."""

        def _unhandled() -> None:
            raise RuntimeError(f"Unhandled view event: {event}")

        {AustinView.Event.QUIT: self.shutdown}.get(event, _unhandled)()

    async def start(self, args: List[str]) -> None:
        """Start Austin and catch any exceptions."""
        try:
            await super().start(args)
        except AustinTerminated:
            pass
        except Exception as e:
            self.shutdown(e)

    def run(self) -> None:
        """Run the TUI."""
        loop = asyncio.get_event_loop()

        try:
            print("🏁 Starting the Austin TUI ...", end="\r")
            austin_task = loop.create_task(
                self.start(AustinTUIArgumentParser.to_list(self._args))
            )
            loop.run_forever()
            if not austin_task.done():
                austin_task.cancel()
        except AustinError as e:
            self.shutdown(e)
        except KeyboardInterrupt:
            self.shutdown()

    def shutdown(self, exception: Optional[Exception] = None) -> None:
        """Shutdown the TUI."""
        try:
            self.terminate()
        except AustinError:
            pass

        self._view.close()

        if exception:
            message = exception.args[0]
            if message[0] == "(":
                _, _, message = message.partition(") ")
            _print(message)

        loop = asyncio.get_event_loop()
        loop.stop()

        pending = [task for task in _get_all_tasks() if not task.done()]
        if pending:
            try:
                done, _ = loop.run_until_complete(asyncio.wait(pending))
                for t in done:
                    try:
                        res = t.result()
                        if res:
                            print(res)
                    except (AustinError, asyncio.CancelledError):
                        pass
            except Exception:
                pass


def main() -> None:
    """Main function."""
    if sys.platform == "win32":
        asyncio.set_event_loop(asyncio.ProactorEventLoop())

    tui = AustinTUI()

    # -- This is just for debugging --
    # def _handler(loop, context):
    #     tui._view.close()
    #     loop.stop()
    #
    #     from austin_tui import write_exception_to_file
    #
    #     write_exception_to_file(context["exception"])
    #
    # asyncio.get_event_loop().set_exception_handler(_handler)

    tui.run()


if __name__ == "__main__":
    main()
