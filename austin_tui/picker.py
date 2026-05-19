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
from typing import List
from typing import NamedTuple
from typing import Optional
from typing import cast

import psutil

from austin_tui.view import EventHandler
from austin_tui.view import View
from austin_tui.view import ViewBuilder
from austin_tui.view.palette import Palette
from austin_tui.widgets.markup import AttrString
from austin_tui.widgets.markup import AttrStringChunk


class PythonProcess(NamedTuple):
    """A Python process entry for the picker."""

    pid: int
    name: str
    cmdline: List[str]


def _get_python_processes() -> List[PythonProcess]:
    procs = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            name = proc.info["name"] or ""
            if "python" not in name.lower():
                continue
            cmdline: List[str] = proc.info["cmdline"] or []
            procs.append(PythonProcess(proc.info["pid"], name, cmdline))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return sorted(procs, key=lambda p: p.pid)


def _pid_cell(pid: int, color: int, selected: bool) -> AttrString:
    astr = AttrString()
    astr.append(AttrStringChunk(f"{pid:>7}", color, False, selected))
    astr.append(AttrStringChunk("  ", 0, False, selected))
    return astr


def _cmdline_cell(proc: PythonProcess, palette: Palette, selected: bool) -> AttrString:
    """Build a syntax-highlighted AttrString for a process command line.

    Colors:
      proc_exec  — executable basename (bold)
      proc_path  — directory prefix of executable
      proc_flag  — tokens starting with -
      proc_arg   — positional args / option values
    """
    astr = AttrString()
    tokens = proc.cmdline if proc.cmdline else [proc.name]

    for i, token in enumerate(tokens):
        if i == 0:
            slash = token.rfind("/")
            if slash >= 0:
                path_c = palette.get_color("proc_path")
                exec_c = palette.get_color("proc_exec")
                astr.append(AttrStringChunk(token[: slash + 1], path_c, False, selected))
                astr.append(AttrStringChunk(token[slash + 1 :], exec_c, True, selected))
            else:
                exec_c = palette.get_color("proc_exec")
                astr.append(AttrStringChunk(token, exec_c, True, selected))
        elif token.startswith("-"):
            flag_c = palette.get_color("proc_flag")
            astr.append(AttrStringChunk(token, flag_c, False, selected))
        else:
            arg_c = palette.get_color("proc_arg")
            astr.append(AttrStringChunk(token, arg_c, False, selected))

        if i < len(tokens) - 1:
            astr.append(AttrStringChunk(" ", 0, False, selected))

    return astr


class PickerView(View):
    """Interactive process picker view."""

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self._processes: List[PythonProcess] = []
        self._selected: int = 0
        self._selected_pid: Optional[int] = None

    @property
    def selected_pid(self) -> Optional[int]:
        """The PID chosen by the user, or None if the picker was dismissed."""
        return self._selected_pid

    def populate(self, processes: List[PythonProcess]) -> None:
        """Load the process list and render the initial table."""
        self._processes = processes
        self._selected = 0
        self._refresh_table()

    def _refresh_table(self) -> None:
        palette = self.palette
        pid_color = palette.get_color("proc_pid")
        data = [
            [
                _pid_cell(proc.pid, pid_color, i == self._selected),
                _cmdline_cell(proc, palette, i == self._selected),
            ]
            for i, proc in enumerate(self._processes)
        ]
        self.proc_table.set_data(data)  # type: ignore[attr-defined]
        self.proc_table.draw()  # type: ignore[attr-defined]
        self.proc_scroll.refresh()  # type: ignore[attr-defined]

    async def on_up(self) -> bool:
        """Move selection up."""
        if self._selected > 0:
            self._selected -= 1
            self._refresh_table()
            scroll = self.proc_scroll  # type: ignore[attr-defined]
            if self._selected < scroll.curr_y:
                scroll.scroll_up()
            return True
        return False

    async def on_down(self) -> bool:
        """Move selection down."""
        if self._selected < len(self._processes) - 1:
            self._selected += 1
            self._refresh_table()
            scroll = self.proc_scroll  # type: ignore[attr-defined]
            if self._selected >= scroll.curr_y + scroll.size.y:
                scroll.scroll_down()
            return True
        return False

    async def on_select(self) -> bool:
        """Confirm selection and close the picker."""
        if self._processes:
            self._selected_pid = self._processes[self._selected].pid
        self.close()
        return False

    async def on_quit(self) -> bool:
        """Dismiss the picker without selecting."""
        self.close()
        return False


async def _run_picker(view: PickerView, processes: List[PythonProcess]) -> None:
    view.open()
    view.populate(processes)
    assert view.root_widget is not None
    view.root_widget.refresh()
    if view._input_task is not None:
        try:
            await view._input_task
        except asyncio.CancelledError:
            pass


def pick_python_process() -> Optional[int]:
    """Show an interactive process picker. Returns the chosen PID or None."""
    processes = _get_python_processes()
    if not processes:
        return None

    builder = ViewBuilder.from_resource("austin_tui.view", "picker.austinui")
    view: PickerView = builder.build()  # type: ignore[assignment]
    builder.autoconnect()
    # "\n" and "\r" can't be expressed as XML attribute values, so wire Enter manually.
    _select = cast(EventHandler, view.on_select)
    view.connect("\n", _select)
    view.connect("\r", _select)
    view.connect("KEY_ENTER", _select)

    asyncio.run(_run_picker(view, processes))

    return view.selected_pid
