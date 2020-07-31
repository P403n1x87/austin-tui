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
from typing import Any

from austin_tui.controllers.austin import (
    AustinController,
    AustinEvent,
    AustinProfileMode,
    ThreadNav,
)
from austin_tui.controllers.system import (
    fmt_time as _fmt_time,
    SystemController,
    SystemEvent,
)
from austin_tui.view import View
from austin_tui.widgets.markup import AttrString, AttrStringChunk


# ---- AustinView -------------------------------------------------------------


class AustinView(View):
    """Austin view."""

    def __init__(
        self, name: str, mode: AustinProfileMode = AustinProfileMode.TIME
    ) -> None:
        super().__init__(name)

        self.mode = mode

        # Create controllers
        self._austin_controller = AustinController(self)
        self._system_controller = SystemController(self)

        self._update_task = asyncio.get_event_loop().create_task(self.update_loop())

    def on_quit(self) -> bool:
        """Handle Quit event."""
        raise KeyboardInterrupt("Quit signal")

    def on_next_thread(self) -> bool:
        """Handle next thread event."""
        if self._austin_controller.push(AustinEvent.CHANGE_THREAD, ThreadNav.NEXT):
            self.table.draw()
            self.stats_view.refresh()
            return True
        return False

    def on_previous_thread(self) -> bool:
        """Handle previous thread event."""
        if self._austin_controller.push(AustinEvent.CHANGE_THREAD, ThreadNav.PREV):
            self.table.draw()
            self.stats_view.refresh()
            return True
        return False

    def on_full_mode_toggled(self) -> bool:
        """Handle Full Mode toggle."""
        self.full_mode_cmd.toggle()
        self._austin_controller.push(AustinEvent.TOGGLE_FULL_MODE)
        self.table.draw()
        self.stats_view.refresh()
        return True

    def on_save(self, data: Any = None) -> bool:
        """Handle Save event."""
        self.notification.set_text("Saving collected statistics ...")
        self.root_widget.refresh()
        return self._austin_controller.push(AustinEvent.SAVE)

    def on_table_up(self, data: Any = None) -> bool:
        """Handle Up Arrow on the table widget."""
        self.stats_view.scroll_up()
        self.stats_view.refresh()
        return False

    def on_table_down(self, data: Any = None) -> bool:
        """Handle Down Arrow on the table widget."""
        self.stats_view.scroll_down()
        self.stats_view.refresh()
        return False

    def on_table_pgup(self, data: Any = None) -> bool:
        """Handle Page Up on the table widget."""
        self.stats_view.scroll_up(self.table.height - 1)
        self.stats_view.refresh()
        return False

    def on_table_pgdown(self, data: Any = None) -> bool:
        """Handle Page Down on the table widget."""
        self.stats_view.scroll_down(self.table.height - 1)
        self.stats_view.refresh()
        return False

    def open(self) -> None:
        """Open the view."""
        super().open()

        self._austin_controller.push(AustinEvent.START)
        self._system_controller.push(SystemEvent.START)
        self.logo.set_color("running")

        self.profile_mode.set_text(f"{self.mode.value} Profile")

        self.table.draw()
        self.table.refresh()

    def _update(self) -> None:
        if self._austin_controller.push(AustinEvent.UPDATE):
            self.table.draw()
        self._system_controller.push(SystemEvent.UPDATE)

    async def update_loop(self) -> None:
        """The UI update loop."""
        await self._input_event.wait()

        while self.is_open and self.root_widget:
            try:
                self._update()
                self.root_widget.refresh()
            except Exception as e:
                from austin_tui import write_exception_to_file

                write_exception_to_file(e)
                raise KeyboardInterrupt()

            await asyncio.sleep(1)

    def stop(self) -> None:
        """Stop Austin view."""
        if not self.is_open or not self.root_widget:
            return

        self._update_task.cancel()
        self.logo.set_color("stopped")
        self.cpu.set_text("--%")
        self.mem.set_text("--M")

        self._system_controller.push(SystemEvent.STOP)
        self._austin_controller.push(AustinEvent.UPDATE)

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
