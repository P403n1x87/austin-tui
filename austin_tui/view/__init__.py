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
import sys
from abc import ABC
from asyncio.coroutines import iscoroutine
from collections import defaultdict
from typing import Any
from typing import Callable
from typing import Coroutine
from typing import Dict
from typing import List
from typing import Optional
from typing import TextIO
from typing import Type
from typing import Union

from importlib_resources import files
from lxml.etree import Element
from lxml.etree import QName
from lxml.etree import _Comment as Comment
from lxml.etree import fromstring as parse_xml_string
from lxml.etree import parse as parse_xml_stream

import austin_tui.widgets.catalog as catalog
from austin_tui.view.palette import Palette
from austin_tui.widgets import Container
from austin_tui.widgets import Rect
from austin_tui.widgets import Widget
from austin_tui.widgets.markup import AttrString
from austin_tui.widgets.markup import markup


EventHandler = Callable[[Optional[Any]], bool]


class _ClassNotFoundError(Exception):
    pass


def _find_class(class_name: str) -> Type:
    try:
        # Try to get a class from the standard catalog
        return getattr(catalog, class_name)
    except AttributeError:
        # Try from any of the loaded modules
        for _, module in sys.modules.items():
            try:
                return getattr(module, class_name)
            except AttributeError:
                pass

    raise _ClassNotFoundError(f"Cannot find class '{class_name}'")


class ViewBuilderError(Exception):
    """View builder generic error."""

    pass


def _issignal(node: Element) -> bool:
    return QName(node).localname == "signal"


def _ispalette(node: Element) -> bool:
    return QName(node).localname == "palette"


def _validate_ns(node: Element) -> None:
    if QName(node).namespace != "http://austin.p403n1x87.com/ui":
        raise ViewBuilderError(f"Node '{node}' has invalid namespace")


class View(ABC):
    """View object.

    All coroutines are collected and scheduled for execution when the view is
    opened.
    """

    def __init__(self, name: str) -> None:
        self._tasks: List[asyncio.Task] = []

        self._event_handlers: Dict[str, List[EventHandler]] = defaultdict(list)

        self._open = False

        self.name = name
        self.palette = Palette()
        self.root_widget = None

    def _create_tasks(self) -> None:
        loop = asyncio.get_event_loop()
        event_handlers = set(_ for hs in self._event_handlers.values() for _ in hs)
        self._tasks = [
            loop.create_task(coro())
            for coro in (
                attr
                for attr in (getattr(self, name) for name in dir(self))
                if callable(attr)
                and asyncio.iscoroutinefunction(attr)
                and attr not in event_handlers
            )
        ]

    def on_exception(self, exc: Exception) -> None:
        """Default task exception callback.

        This simply closes the view and re-raises the exception. Override in
        sub-classes with custom logic.
        """
        raise exc

    async def _input_loop(self) -> None:
        try:
            if not self.root_widget:
                raise RuntimeError("Missing root widget")

            while self._open:
                await asyncio.sleep(0.015)

                if not self.root_widget._win:
                    continue

                # Handle user input on the root widget
                try:
                    event = self.root_widget._win.getkey()
                    if event in self._event_handlers:
                        done, pending = await asyncio.wait(
                            [_() for _ in self._event_handlers[event]]
                        )
                        assert not pending
                        if any(_.result() for _ in done):
                            self.root_widget.refresh()
                except (KeyError, curses.error):
                    pass

                # Retrieve the result of finished tasks
                finished_tasks = []
                running_tasks = []
                for task in self._tasks:
                    if task.done():
                        finished_tasks.append(task)
                    else:
                        running_tasks.append(task)
                self._tasks = running_tasks

                for task in finished_tasks:
                    task.result()
        except Exception as exc:
            self.on_exception(exc)

    def _build(self, node: Element) -> Widget:
        _validate_ns(node)
        widget_class = QName(node).localname
        try:
            # Try to get a widget from the standard catalog
            widget = _find_class(widget_class)(**node.attrib)
        except _ClassNotFoundError as e:
            raise ViewBuilderError(f"Unknown widget: {widget_class}") from e

        widget.view = self
        setattr(self, widget.name, widget)

        return widget

    def connect(self, event: str, handler: EventHandler) -> None:
        """Connect event handlers."""
        if handler is None:
            raise ValueError(f"{handler} is not a valid handler")
        self._event_handlers[event].append(handler)

    def markup(self, text: Any) -> AttrString:
        """Convert a markup string into an attribute string."""
        return markup(str(text), self.palette)

    def open(self) -> None:
        """Open the view.

        Calling this method not only shows the TUI on screen, but also collects
        and schedules all the coroutines on the instance with the event loop.
        """
        if not self.root_widget:
            raise RuntimeError("View has no root widget")

        self.root_widget.show()
        self._open = True

        self.palette.init()

        self.root_widget.resize(Rect(0, self.root_widget.get_size()))
        self.root_widget.draw()
        self.root_widget.refresh()

        self._create_tasks()

    def submit_task(
        self,
        task: Union[
            asyncio.Task,
            Coroutine[None, None, None],
            Callable[[], Any],
        ],
    ) -> None:
        """Submit a task to run concurrently in the event loop.

        A task can be an :class:`asyncio.Task` object, a coroutine or a plain
        callable object. Any exception thrown within the task can be retrieved
        from the ``on_exception`` callback.
        """
        if isinstance(task, asyncio.Task):
            self._tasks.append(task)
        elif iscoroutine(task):
            self._tasks.append(asyncio.create_task(task))  # type: ignore[arg-type]
        else:
            self._tasks.append(asyncio.get_event_loop().run_in_executor(None, task))  # type: ignore[arg-type]

    def close(self) -> None:
        """Close the view."""
        if self._open and self.root_widget:
            self.root_widget.hide()

        for task in self._tasks:
            task.cancel()
            if task.done():
                task.result()

        self._open = False

    @property
    def is_open(self) -> bool:
        """Whether the view is open."""
        return self._open


class ViewBuilder:
    """View builder class."""

    def __init__(self, view_node: Element) -> None:
        _validate_ns(view_node)
        self._root = view_node
        self._signals: Dict[str, str] = {}
        self._autoconnect = False
        self._view: Optional[View] = None

    def _parse(self) -> View:
        view_class = QName(self._root).localname
        try:
            view = _find_class(view_class)(**self._root.attrib)
        except _ClassNotFoundError:
            raise ViewBuilderError(f"Cannot find view class '{view_class}'") from None

        root, *rest = self._root
        view.root_widget = view._build(root)
        view.connect("KEY_RESIZE", view.root_widget.on_resize)

        def _add_children(widget: Container, node: Element) -> None:
            for child in node:
                if isinstance(child, Comment):
                    continue
                child_widget = view._build(child)
                child_widget.win = widget.win
                _add_children(child_widget, child)
                widget.add_child(child_widget)

        _add_children(view.root_widget, root)

        for node in rest:
            if isinstance(node, Comment):
                continue
            _validate_ns(node)
            if _issignal(node):
                event = node.attrib["key"]
                handler = node.attrib["handler"]
                self._signals[event] = handler
            elif _ispalette(node):
                for color in node:
                    if isinstance(color, Comment):
                        continue
                    view.palette.add_color(**color.attrib)
            else:
                raise ViewBuilderError(f"Unknown view element: {node}")

        return view

    def autoconnect(self, *controllers: Any) -> None:
        """Auto-connect event handlers.

        If a view has been built, this method allows passing objects that hold
        all the necessary event handlers that are declared in the UI resource.
        Any unconnected handlers will cause an exception to be raised.
        """
        if self._view is None:
            raise RuntimeError("View has not been built yet.")
        if self._autoconnect:
            raise RuntimeError("Event handlers already autoconnected.")

        view = self._view
        holders = [view, *controllers]
        for event, handler in self._signals.items():
            try:
                methods = [getattr(_, handler) for _ in holders if hasattr(_, handler)]
                if not methods:
                    raise AttributeError()
                for method in methods:
                    view.connect(event=event, handler=method)
            except Exception as e:
                raise ViewBuilderError(
                    f"Cannot autoconnect handlers for '{handler}' to event '{event}'"
                ) from e

        self._autoconnect = True

    def build(self) -> View:
        """Build the view."""
        self._view = view = self._parse()
        return view

    @classmethod
    def from_stream(cls, stream: TextIO) -> "ViewBuilder":
        """Build view from a stream."""
        return cls(parse_xml_stream(stream).getroot())

    @classmethod
    def from_resource(cls, module: str, resource: str) -> "ViewBuilder":
        """Build view from a resource file."""
        return cls(
            parse_xml_string(
                files(module).joinpath(resource).read_text(encoding="utf8").encode()
            )
        )
