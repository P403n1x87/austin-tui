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
import curses

from austin_tui.widgets import Widget


class Window(Widget):
    def __init__(self):
        super().__init__()
        self._scr = None

        self._visible = False

        self._input_event = asyncio.Event()
        self._input_task = asyncio.get_event_loop().create_task(self._input_loop())

    async def _input_loop(self):
        await self._input_event.wait()
        while self._visible:
            await asyncio.sleep(0.015)

            if not self._scr:
                continue

            # self._scr.refresh()
            try:
                self.dispatch(self._scr.getkey())
            except curses.error:
                pass

            except Exception as e:
                from austin_tui import write_exception_to_file

                write_exception_to_file(e)
                raise KeyboardInterrupt()

    def refresh(self):
        try:
            return super().refresh()
        finally:
            self._scr.refresh()

    def show(self):

        self._scr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self._scr.keypad(1)
        try:
            curses.start_color()
        except:
            pass

        curses.use_default_colors()
        curses.curs_set(False)

        self._scr.clear()
        self._scr.timeout(0)  # non-blocking for async I/O
        self._scr.nodelay(True)

        try:
            self.build_ui(self._scr)
        except Exception as e:
            from austin_tui import write_exception_to_file

            write_exception_to_file(e)
            raise e
        self.refresh()

        self._visible = True

        self._input_event.set()
        # self._scr.refresh()
        # try:
        #     self.table_pad.getkey()
        # except curses.error:
        #     pass

    def hide(self):
        self._visible = False

        # self._scr.clrtoeol()
        # self._scr.refresh()

        self._scr.keypad(0)
        curses.echo()
        curses.nocbreak()
        curses.endwin()

        self._input_task.cancel()

    def run(self, screen):
        pass

    def build_ui(self):
        pass

    def get_size(self):
        return self._scr.getmaxyx()

    def get_screen(self):
        return self._scr

    def is_visible(self):
        return self._visible
