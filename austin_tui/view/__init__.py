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

from austin_tui.controllers.system import SystemController, SystemEvent
from austin_tui.controllers.austin import (
    AustinController,
    AustinEvent,
    ThreadNav,
    AustinProfileMode,
)
from austin_tui.widgets.command_bar import CommandBar
from austin_tui.widgets.label import BarPlot, Label, Line, TaggedLabel, TextAlign
from austin_tui.widgets.pad import Table
from austin_tui.widgets.window import Window
from austin_tui.view.palette import Color, init as init_palette


# ---- Widget Positions -------------------------------------------------------

TITLE_LINE = (0, 0)
LOGO = (1, 0)
LOGO_WIDTH = 13
INFO_AREA_X = LOGO_WIDTH + 1

PID = (TITLE_LINE[0] + 1, INFO_AREA_X)

CMD_LINE = (PID[0], INFO_AREA_X + 12)

THREAD = (PID[0] + 1, INFO_AREA_X)
THREAD_NUM = (PID[0] + 1, INFO_AREA_X + 24)
THREAD_TOTAL = (PID[0] + 1, INFO_AREA_X + 31)

SAMPLES = (THREAD[0] + 1, INFO_AREA_X)

DURATION = (SAMPLES[0], INFO_AREA_X + 18)

CPU = (THREAD[0], INFO_AREA_X + 40)
CPU_PLOT = (THREAD[0], INFO_AREA_X + 54)

MEM = (SAMPLES[0], INFO_AREA_X + 40)
MEM_PLOT = (SAMPLES[0], INFO_AREA_X + 54)

TABHEAD_LINE = (THREAD[0] + 2, 0)
TAB_START = (TABHEAD_LINE[0] + 1, 0)

TABHEAD_TEMPLATE = " {:^6}  {:^6}  {:^6}  {:^6}  {}"
TABHEAD_FUNCTION_PAD = len(TABHEAD_TEMPLATE.format("", "", "", "", ""))


# ---- Local Helpers ----------------------------------------------------------


def ellipsis(text, length):
    if len(text) <= length:
        return text

    try:
        f, rest = text.split()
    except ValueError:
        f, rest = text, ""

    if len(f) > length:
        return f[: length - 3] + "..."

    if len(f) + 6 <= length:
        length -= len(f) + 1
        return f + " " + rest[: (length >> 1) - 2] + "..." + rest[-(length >> 1) + 1 :]

    return f


# ---- AustinView -------------------------------------------------------------


class AustinView(Window):
    def __init__(self, mode: AustinProfileMode = AustinProfileMode.TIME):
        super().__init__()

        self.current_thread = None
        self.current_thread_index = None
        self.max_memory = 0
        self.current_cpu = 0
        self.current_memory = 0
        self.is_full_view = False
        self.mode = mode

        # Create controllers
        self._austin_controller = AustinController(self)
        self._system_controller = SystemController(self)

        self._update_task = asyncio.get_event_loop().create_task(self.update_loop())

    def build_ui(self, scr):

        init_palette()

        # ---- Logo -----------------------------------------------------------

        self.add_child(
            "title_line",
            Line(
                *TITLE_LINE, text=f" Austin  TUI  {self.mode.value} Profile", bold=True
            ),
        )

        self.add_child(
            "logo", Label(*LOGO, text=["  _________  ", "  ⎝__⎠ ⎝__⎠  "], bold=True)
        )

        # ---- Process Information --------------------------------------------

        self.add_child("pid", TaggedLabel(*PID, width=5, bold=True))

        # ---- Command Line ---------------------------------------------------

        self.add_child(
            "cmd_line", TaggedLabel(*CMD_LINE, tag={"text": "CMD"}, bold=True)
        )

        # ---- Threads --------------------------------------------------------

        self.add_child("thread_name", TaggedLabel(*THREAD, width=24, bold=True))

        self.add_child("thread_total", Label(*THREAD_TOTAL, width=5))

        self.add_child(
            "thread_num", Label(*THREAD_NUM, width=5, color=Color.THREAD, bold=True)
        )

        # ---- Samples --------------------------------------------------------

        self.add_child(
            "samples",
            TaggedLabel(*SAMPLES, width=8, tag={"text": "Samples"}, bold=True),
        )

        # ---- Duration -------------------------------------------------------

        self.add_child(
            "duration",
            TaggedLabel(
                *DURATION,
                width=8,
                tag={"text": "Duration"},
                align=TextAlign.RIGHT,
                bold=True,
            ),
        )

        # ---- CPU ------------------------------------------------------------

        self.add_child(
            "cpu",
            TaggedLabel(
                *CPU, width=6, tag={"text": "CPU"}, align=TextAlign.RIGHT, bold=True
            ),
        )
        #
        self.add_child(
            "cpu_plot", BarPlot(*CPU_PLOT, scale=100, init=0, color=Color.CPU)
        )

        # ---- Memory ---------------------------------------------------------

        self.add_child(
            "mem",
            TaggedLabel(
                *MEM, width=6, tag={"text": "MEM"}, align=TextAlign.RIGHT, bold=True
            ),
        )

        self.add_child("mem_plot", BarPlot(*MEM_PLOT, init=0, color=Color.MEMORY))

        # ---- Footer ---------------------------------------------------------

        self.add_child(
            "cmd_bar",
            CommandBar(
                {
                    "Exit": " Q ",
                    "PrevThread": "PgUp",
                    "NextThread": "PgDn",
                    "ToggleFullView": " F ",
                }
            ),
        )

        # Conect signal handlers
        self.connect("q", self.on_quit)
        self.connect("f", self.on_full_mode_toggled)
        self.connect("KEY_NPAGE", self.on_pgdown)
        self.connect("KEY_PPAGE", self.on_pgup)

        # ---- Table ----------------------------------------------------------

        self.add_child(
            "table_header",
            Line(
                *TABHEAD_LINE,
                text=TABHEAD_TEMPLATE.format(
                    "OWN", "TOTAL", "%OWN", "%TOTAL", "FUNCTION"
                ),
                reverse=True,
                bold=True,
            ),
        )
        self.add_child(
            "table_pad",
            Table(
                size_policy=lambda: [
                    (h - TAB_START[0] - self.cmd_bar.get_height(), w)
                    for h, w in [self.get_size()]
                ][0],
                position_policy=lambda: (TAB_START[0], 0),
                columns=[" {:^6} ", " {:^6} ", " {:5.1f}% ", " {:5.1f}% ", " {}"],
            ),
        )

        # ---- END OF UI DEFINITION -------------------------------------------

    # ---- EVENT HANDLERS -----------------------------------------------------

    def on_quit(self):
        raise KeyboardInterrupt("Quit signal")

    def on_pgdown(self):
        self._austin_controller.push(AustinEvent.CHANGE_THREAD, ThreadNav.NEXT)
        self.refresh()

    def on_pgup(self):
        self._austin_controller.push(AustinEvent.CHANGE_THREAD, ThreadNav.PREV)
        self.refresh()

    def on_full_mode_toggled(self):
        self._austin_controller.push(AustinEvent.TOGGLE_FULL_MODE)
        self.table_pad.refresh()

    def show(self):
        super().show()

        self._austin_controller.push(AustinEvent.START)
        self._system_controller.push(SystemEvent.START)
        self.logo.set_color(Color.RUNNING)

    def update(self):
        self._austin_controller.push(AustinEvent.UPDATE)
        self._system_controller.push(SystemEvent.UPDATE)
        self.refresh()

    async def update_loop(self):
        await self._input_event.wait()

        while self.is_visible():
            try:
                self.update()
            except Exception as e:
                from austin_tui import write_exception_to_file

                write_exception_to_file(e)
                raise KeyboardInterrupt()

            await asyncio.sleep(1)

    def stop(self):
        if not self.is_visible():
            return

        self._update_task.cancel()
        self.logo.set_color(Color.STOPPED)
        self.cpu.set_text("--%")
        self.mem.set_text("--M")

        self._system_controller.push(SystemEvent.STOP)
        self._austin_controller.push(AustinEvent.UPDATE)

        self.refresh()
