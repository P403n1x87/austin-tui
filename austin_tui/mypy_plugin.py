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

"""Mypy plugin that infers widget attribute types from .austinui XML resources.

Any View subclass can declare::

    __ui_resource__ = ("austin_tui.view", "tui.austinui")

and the plugin will parse the referenced XML file at type-check time, adding
properly-typed attributes for every named widget it finds.
"""

import importlib.util
import os
from typing import Callable
from typing import Optional
from xml.etree import ElementTree as ET

from mypy.nodes import MDEF
from mypy.nodes import AssignmentStmt
from mypy.nodes import NameExpr
from mypy.nodes import StrExpr
from mypy.nodes import SymbolTableNode
from mypy.nodes import TypeInfo
from mypy.nodes import Var
from mypy.plugin import ClassDefContext
from mypy.plugin import Plugin
from mypy.types import Instance


# .austinui XML namespace
_NAMESPACE = "http://austin.p403n1x87.com/ui"
_NS_PREFIX = f"{{{_NAMESPACE}}}"

# Maps XML element localname → fully-qualified mypy type name
_WIDGET_TYPES: dict[str, str] = {
    "Box": "austin_tui.widgets.box.Box",
    "BarPlot": "austin_tui.widgets.label.BarPlot",
    "CommandBar": "austin_tui.widgets.command_bar.CommandBar",
    "FlameGraph": "austin_tui.widgets.graph.FlameGraph",
    "Label": "austin_tui.widgets.label.Label",
    "Line": "austin_tui.widgets.label.Line",
    "ScrollView": "austin_tui.widgets.scroll.ScrollView",
    "Selector": "austin_tui.widgets.selector.Selector",
    "Table": "austin_tui.widgets.table.Table",
    "ToggleLabel": "austin_tui.widgets.label.ToggleLabel",
    "Window": "austin_tui.widgets.window.Window",
}

_VIEW_BASE = "austin_tui.view.View"


# ---------------------------------------------------------------------------
# XML helpers
# ---------------------------------------------------------------------------


def _find_resource(package: str, resource: str) -> Optional[str]:
    """Return the filesystem path for a package resource, or None."""
    try:
        spec = importlib.util.find_spec(package)
        if spec is None or spec.origin is None:
            return None
        package_dir = os.path.dirname(spec.origin)
        candidate = os.path.join(package_dir, resource)
        return candidate if os.path.isfile(candidate) else None
    except (ModuleNotFoundError, ValueError):
        return None


def _extract_widgets(xml_path: str) -> dict[str, str]:
    """Return {widget_name: widget_type_fullname} for every named widget in the XML."""
    tree = ET.parse(xml_path)
    widgets: dict[str, str] = {}

    def _walk(el: ET.Element) -> None:
        tag = el.tag
        if tag.startswith(_NS_PREFIX):
            localname = tag[len(_NS_PREFIX) :]
            name = el.attrib.get("name")
            if name and localname in _WIDGET_TYPES:
                widgets[name] = _WIDGET_TYPES[localname]
        for child in el:
            _walk(child)

    _walk(tree.getroot())
    return widgets


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _read_ui_resource(ctx: ClassDefContext) -> Optional[tuple[str, str]]:
    """Read ``__ui_resource__ = "resource"`` from the class body.

    The package is derived from the class's own module name so it never needs
    to be spelled out explicitly.
    """
    for stmt in ctx.cls.defs.body:
        if not isinstance(stmt, AssignmentStmt):
            continue
        for lvalue in stmt.lvalues:
            if (
                not isinstance(lvalue, NameExpr)
                or lvalue.name != "__ui_resource__"
            ):
                continue
            if isinstance(stmt.rvalue, StrExpr):
                module = (
                    ctx.cls.info.module_name
                )  # e.g. "austin_tui.view.austin"
                package = module.rsplit(".", 1)[0]  # e.g. "austin_tui.view"
                return (package, stmt.rvalue.value)
    return None


# ---------------------------------------------------------------------------
# Plugin hook
# ---------------------------------------------------------------------------


def _inject_widget_attrs(ctx: ClassDefContext) -> None:
    """Inject typed widget attributes derived from the class's .austinui resource."""
    resource_spec = _read_ui_resource(ctx)
    if resource_spec is None:
        return

    package, resource = resource_spec
    xml_path = _find_resource(package, resource)
    if xml_path is None:
        ctx.api.fail(
            f"austin-tui mypy plugin: cannot locate resource '{resource}' "
            f"in package '{package}'",
            ctx.cls,
        )
        return

    try:
        widgets = _extract_widgets(xml_path)
    except ET.ParseError as exc:
        ctx.api.fail(
            f"austin-tui mypy plugin: failed to parse '{xml_path}': {exc}",
            ctx.cls,
        )
        return

    cls_info = ctx.cls.info

    for attr_name, type_fullname in widgets.items():
        # Don't override explicitly declared attributes
        if attr_name in cls_info.names:
            continue

        type_sym = ctx.api.lookup_fully_qualified_or_none(type_fullname)
        if type_sym is None or not isinstance(type_sym.node, TypeInfo):
            continue

        typ = Instance(type_sym.node, [])
        var = Var(attr_name, typ)
        var.info = cls_info
        var._fullname = f"{cls_info.fullname}.{attr_name}"
        cls_info.names[attr_name] = SymbolTableNode(MDEF, var)


class AustinTUIPlugin(Plugin):
    """Mypy plugin for austin-tui."""

    def get_base_class_hook(
        self, fullname: str
    ) -> Optional[Callable[[ClassDefContext], None]]:
        """Inject widget attributes into View subclasses with __ui_resource__."""
        if fullname == _VIEW_BASE:
            return _inject_widget_attrs
        return None


def plugin(version: str) -> type[AustinTUIPlugin]:
    """Return the plugin class for mypy."""
    return AustinTUIPlugin
