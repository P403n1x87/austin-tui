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
from enum import Enum
from typing import Any
from typing import Callable
from typing import Optional

from austin_tui import AustinProfileMode
from austin_tui.adapters import fmt_time as _fmt_time
from austin_tui.view import View
from austin_tui.widgets.markup import AttrString
from austin_tui.widgets.markup import AttrStringChunk


# ---- AustinView -------------------------------------------------------------


class AustinView(View):
    """Austin view."""

    class Event(Enum):
        """Austin View Events."""

        EXCEPTION = 0
        QUIT = 1

    def __init__(
        self,
        name: str,
        mode: AustinProfileMode = AustinProfileMode.TIME,
        callback: Optional[Callable[["Event", Optional[Any]], None]] = None,
    ) -> None:
        super().__init__(name)

        self.mode = mode
        self.callback = callback

        self._stopped = False

    def on_exception(self, exc: Exception) -> None:
        """The on exception Austin view handler."""
        if not self.callback:
            raise RuntimeError(
                "AustinTUI requires a callback to handle exception events."
            )
        self.callback(self.Event.EXCEPTION, exc)

    async def on_quit(self) -> bool:
        """Handle Quit event."""
        if not self.callback:
            raise RuntimeError("AustinTUI requires a callback to handle quit events.")
        self.callback(self.Event.QUIT, None)
        return False

    async def on_full_mode_toggled(self) -> bool:
        """Handle Full Mode toggle."""
        if self.graph_cmd.state:
            return False

        self.full_mode_cmd.toggle()
        return True

    async def on_graph_toggled(self) -> bool:
        """Handle graph visualisation toggling."""
        self.graph_cmd.toggle()
        self.dataview_selector.refresh()
        if self.graph_cmd.state:
            self.full_mode_cmd.set_color("disabled")
        else:
            self.full_mode_cmd.toggle()
            self.full_mode_cmd.toggle()
        return True

    async def on_save(self, data: Any = None) -> bool:
        """Handle Save event."""
        self.notification.set_text("Saving collected statistics ...")
        return True

    async def on_table_up(self, data: Any = None) -> bool:
        """Handle Up Arrow on the table widget."""
        view = self.flame_view if self.graph_cmd.state else self.stats_view

        view.scroll_up()
        view.refresh()
        return False

    async def on_table_down(self, data: Any = None) -> bool:
        """Handle Down Arrow on the table widget."""
        view = self.flame_view if self.graph_cmd.state else self.stats_view

        view.scroll_down()
        view.refresh()
        return False

    async def on_table_pgup(self, data: Any = None) -> bool:
        """Handle Page Up on the table widget."""
        view = self.flame_view if self.graph_cmd.state else self.stats_view

        view.scroll_page_up()
        view.refresh()
        return False

    async def on_table_pgdown(self, data: Any = None) -> bool:
        """Handle Page Down on the table widget."""
        view = self.flame_view if self.graph_cmd.state else self.stats_view

        view.scroll_page_down()
        view.refresh()
        return False

    async def on_table_home(self, _: Any = None) -> bool:
        """Handle Home key on the table widget."""
        view = self.flame_view if self.graph_cmd.state else self.stats_view

        view.top()
        view.refresh()

        return False

    async def on_table_end(self, _: Any = None) -> bool:
        """Handle End key on the table widget."""
        view = self.flame_view if self.graph_cmd.state else self.stats_view

        view.bottom()
        view.refresh()

        return False

    async def on_play_pause(self, _: Any = None) -> bool:
        """Play/pause handler."""
        if self._stopped:
            return False

        self.play_pause_cmd.toggle()
        self.play_pause_label.set_text(
            "Resume" if self.play_pause_cmd.state else "Pause"
        )
        self.logo.set_color("paused" if self.play_pause_cmd.state else "running")
        return True

    def open(self) -> None:
        """Open the view."""
        super().open()

        self.logo.set_color("running")

        self.profile_mode.set_text(f"{self.mode.value} Profile")

        self.table.draw()
        self.table.refresh()

    def stop(self) -> None:
        """Stop Austin view."""
        if not self.is_open or not self.root_widget:
            return

        self._stopped = True
        self.logo.set_color("stopped")
        self.cpu.set_text("--% ")
        self.mem.set_text("--M ")
        self.play_pause_cmd.set_color("disabled")

        self.table.draw()
        self.root_widget.refresh()

    def fmt_time(self, t: int, active: bool = True) -> AttrString:
        """Format time value."""
        time = f"{_fmt_time(t):^8}"
        return self.markup(f"<inactive>{time}</inactive>" if not active else time)

    def fmt_mem(self, s: int, active: bool = True) -> AttrString:
        """Format memory value."""
        units = ["B", "K", "M"]

        i = 0
        ss = s
        while ss >= 1024 and i < len(units) - 1:
            i += 1
            ss >>= 10
        mem = f"{ss: 6d}{units[i]} "
        return self.markup(f"<inactive>{mem}</inactive>" if not active else mem)

    def color_level(self, value: float, active: bool = True) -> int:
        """Return the value heat."""
        prefix = ("i" if not active else "") + "heat"
        for stop in [20, 40, 60, 80, 100]:
            if value <= stop:
                return self.palette.get_color(prefix + str(stop))
        return self.palette.get_color(prefix + "100")

    def _scaler(self, ratio: float, active: bool) -> AttrStringChunk:
        return AttrStringChunk(
            f"{min(100, ratio):6.1f}% ", color=self.color_level(ratio, active)
        )

    def scale_memory(
        self, memory: int, max_memory: int, active: bool = True
    ) -> AttrStringChunk:
        """Scale a memory value and return an attribute string chunk."""
        return self._scaler(memory / max_memory * 100 if max_memory else 0, active)

    def scale_time(
        self, time: int, duration: int, active: bool = True
    ) -> AttrStringChunk:
        """Scale a time value and return an attribute string chunk."""
        return self._scaler(min(time / 1e4 / duration, 100), active)

    def set_mode(self, mode: str) -> None:
        """Set profiling mode."""
        self.profile_mode.set_text(
            " "
            + {
                "wall": "Wall Time Profile",
                "cpu": "CPU Time Profile",
                "memory": "Memory Profile",
            }[mode]
        )
        self.profile_mode.set_color(f"mode_{mode}")

    def set_pid(self, pid: int, children: bool) -> None:
        """Set the PID."""
        self.pid_label.set_text("PPID" if children else "PID")
        self.pid.set_text(self.markup(f"<pid><b>{pid}</b></pid>"))

    def set_python(self, version: str) -> None:
        """Set the Python version."""
        self.python.set_text(".".join([str(_) for _ in version]))
