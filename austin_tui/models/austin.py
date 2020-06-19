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

from austin.stats import AustinStats, InvalidSample, Sample
from time import time


class OrderedSet:
    def __init__(self):
        self._items = []
        self._map = {}

    def __contains__(self, thread):
        return thread in self._map

    def __getitem__(self, i):
        return self._items[i] if isinstance(i, int) else self._map[i]

    def __len__(self):
        return len(self._items)

    def add(self, thread):
        if thread not in self._map:
            self._map[thread] = len(self._items)
            self._items.append(thread)

    def __bool__(self):
        return bool(self._items)

    def __str__(self):
        return type(self).__name__ + str(self._items)

    def __repr__(self):
        return type(self).__name__ + repr(self._items)


class AustinModel:
    __borg__ = {}

    def __init__(self):
        self.__dict__ = self.__borg__

        self._samples = 0
        self._invalids = 0
        self._last_stack = {}
        self._stats = AustinStats()
        self._stats.timestamp = time()

        self._threads = OrderedSet()

    def update(self, raw_sample):
        try:
            sample = Sample.parse(raw_sample)
            self._stats.update(sample)
            self._stats.timestamp = time()
            thread_key = f"{sample.pid}:{sample.thread}"
            self._last_stack[thread_key] = sample
            self._threads.add(thread_key)
        except InvalidSample:
            self._invalids += 1
        finally:
            self._samples += 1

    def get_last_stack(self, thread_key):
        return self._last_stack[thread_key]

    @property
    def stats(self):
        return self._stats

    @property
    def threads(self):
        return self._threads

    @property
    def samples_count(self):
        return self._samples

    @property
    def error_rate(self):
        return self._invalids / self._samples
