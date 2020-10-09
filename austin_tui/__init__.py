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

# TODO: This is for debug purpose only and should be removed.


def write_exception_to_file(e):
    import traceback as tb

    trace = "".join(tb.format_tb(e.__traceback__))
    trace += f"{type(e).__qualname__}: {e}"
    # print(trace)
    with open("/tmp/austin-tui.out", "a") as fout:
        fout.write(trace + "\n")


def fp(text):
    with open("/tmp/austin-tui.out", "a") as fout:
        fout.write(str(text) + "\n")


def catch(f):
    def wrapper(*args, **kwargs):
        try:
            f(*args, **kwargs)
        except Exception as e:
            write_exception_to_file(e)
            raise e

    return wrapper
