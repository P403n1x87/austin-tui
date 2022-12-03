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

from copy import deepcopy
from time import time
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from austin.stats import AustinStats
from austin.stats import AustinStatsType
from austin.stats import InvalidSample
from austin.stats import MetricType
from austin.stats import Sample

from austin_tui import AustinProfileMode


class OrderedSet:
    """Ordered set."""

    def __init__(self) -> None:
        self._items: List[Any] = []
        self._map: Dict[Any, int] = {}

    def __contains__(self, element: Any) -> bool:
        """Check if the set contains the element."""
        return element in self._map

    def __getitem__(self, i: Any) -> Any:
        """Get the i-th item or the index of the given hashable object."""
        return self._items[i] if isinstance(i, int) else self._map[i]

    def __len__(self) -> int:
        """The number of elements in the set."""
        return len(self._items)

    def add(self, element: Any) -> None:
        """Add an element to the set.

        If the element is already in the set, nothing happens.
        """
        if element not in self._map:
            self._map[element] = len(self._items)
            self._items.append(element)

    def __bool__(self) -> bool:
        """Convert to boolean."""
        return bool(self._items)

    def __str__(self) -> str:
        """Representation of the set."""
        return type(self).__name__ + str(self._items)

    def __repr__(self) -> str:
        """Representation of the set."""
        return type(self).__name__ + repr(self._items)


class AustinModel:
    """Austin model."""

    def __init__(self) -> None:
        self.mode = None

        self._samples = 0
        self._invalids = 0
        self._last_stack: Dict[str, Sample] = {}
        self._stats = AustinStats(
            AustinStatsType.MEMORY
            if self.mode is AustinProfileMode.MEMORY
            else AustinStatsType.WALL
        )
        self._stats.timestamp = time()

        self._austin_version: Optional[str] = None
        self._python_version: Optional[str] = None

        self._threads = OrderedSet()
        self._current_thread = 0

        self.metadata: Optional[Dict[str, str]] = None
        self.threshold = 0.0
        self.command_line: Optional[str] = None

    def set_command_line(self, command_line: str) -> None:
        """Set the command line."""
        self.command_line = command_line

    def get_versions(self) -> Tuple[Optional[str], Optional[str]]:
        """Get Austin and Python versions."""
        return self._austin_version, self._python_version

    def set_versions(self, austin_version: str, python_version: str) -> None:
        """Set Austin and Python versions."""
        self._austin_version = austin_version
        self._python_version = python_version

    def set_metadata(self, metadata: Dict[str, str]) -> None:
        """Set the Austin metadata."""
        self.metadata = metadata

    def update(self, raw_sample: str) -> None:
        """Update current statistics with a new sample."""
        try:
            (sample,) = Sample.parse(
                raw_sample,
                MetricType.MEMORY
                if self.mode is AustinProfileMode.MEMORY
                else MetricType.TIME,
            )
            if sample.metric.value < 0:
                return
            self._stats.update(sample)
            self._stats.timestamp = time()
            thread_key = f"{sample.pid}:{sample.thread}"
            self._last_stack[thread_key] = sample
            self._threads.add(thread_key)
        except InvalidSample:
            self._invalids += 1
        finally:
            self._samples += 1

    def get_last_stack(self, thread_key: str) -> Sample:
        """Get the last seen stack for the given thread."""
        return self._last_stack[thread_key]

    @property
    def stats(self) -> AustinStats:
        """The current Austin statistics."""
        return self._stats

    @property
    def threads(self) -> OrderedSet:
        """The seen threads as ordered set."""
        return self._threads

    @property
    def samples_count(self) -> int:
        """Get the sample count."""
        return self._samples

    @property
    def error_rate(self) -> float:
        """Get the error rate."""
        return self._invalids / self._samples

    @property
    def current_thread(self) -> int:
        """Get the currently active thread."""
        return self._current_thread

    @current_thread.setter
    def current_thread(self, n: int) -> None:
        """Set the currently active thread."""
        assert 0 <= n <= len(self._threads)
        self._current_thread = n

    def freeze(self) -> "AustinModel":
        """Freeze the model."""
        return deepcopy(self)
