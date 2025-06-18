from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from flake8_scrapy.ast import (
    UNPARSEABLE,
    get_method_location,
    get_parameter_location,
    load_argument_from_call,
)
from flake8_scrapy.data.settings import SETTINGS
from flake8_scrapy.issues import Issue
from flake8_scrapy.settings import Setting, SettingType

if TYPE_CHECKING:
    from collections.abc import Generator

    from flake8_scrapy.context import Context


# NOTE: getwithbase does not have a default parameter.
GETTER_DEFAULTS = {
    "get": None,
    "getbool": False,
    "getint": 0,
    "getfloat": 0.0,
    "getlist": None,
    "getdict": None,
    "getdictorlist": None,
}
GETTERS = set(GETTER_DEFAULTS) | {"getwithbase"}
SETTING_TYPE_TO_GETTER = {
    SettingType.BOOL: "getbool",
    SettingType.INT: "getint",
    SettingType.FLOAT: "getfloat",
    SettingType.LIST: "getlist",
    SettingType.DICT: "getdict",
    SettingType.DICT_OR_LIST: "getdictorlist",
    SettingType.BASED_DICT: "getwithbase",
}


class SettingsIssueFinder:
    visit_types: tuple[str, ...] = ("Assign", "Call", "Subscript")

    def __init__(self, context: Context | None = None):
        self.context = context

    def find_issues(self, node) -> Generator[Issue, None, None]:
        if isinstance(node, ast.Assign):
            yield from self.find_assign_issues(node)
        elif isinstance(node, ast.Call):
            yield from self.find_call_issues(node)
        elif isinstance(node, ast.Subscript):
            yield from self.find_subscript_issues(node)

    def find_assign_issues(self, node: ast.Assign) -> Generator[Issue, None, None]:
        return
        yield

    def find_call_issues(self, node: ast.Call) -> Generator[Issue, None, None]:
        if isinstance(node.func, ast.Attribute):
            if self.is_settings_object(node.func.value):
                if self.is_wrong_setting_getter_call(node):
                    yield Issue(
                        code=30,
                        summary="wrong setting getter",
                        **get_method_location(node),
                    )
                if self.is_defaultless_getter_call(node):
                    yield Issue(
                        code=31,
                        summary="unneeded setting get",
                        **get_method_location(node),
                    )
                elif self.is_noop_default_getter_call(node):
                    yield Issue(
                        code=29,
                        summary="no-op setting getter default",
                        **get_parameter_location(node, "default", 1),
                    )

    def find_subscript_issues(
        self, node: ast.Subscript
    ) -> Generator[Issue, None, None]:
        if self.is_settings_object(node.value):
            if self.is_wrong_setting_subscript(node):
                yield Issue(
                    code=30,
                    summary="wrong setting getter",
                    line=node.lineno,
                    column=node.col_offset,
                )

    def is_defaultless_getter_call(self, node: ast.Call) -> bool:
        assert isinstance(node.func, ast.Attribute)
        return node.func.attr == "get" and (
            (len(node.args) == 1 and len(node.keywords) == 0)
            or (
                not len(node.args)
                and len(node.keywords) == 1
                and node.keywords[0].arg == "name"
            )
        )

    def is_noop_default_getter_call(self, node: ast.Call) -> bool:
        assert isinstance(node.func, ast.Attribute)
        method_name = node.func.attr
        if method_name not in GETTER_DEFAULTS:
            return False
        argument = load_argument_from_call(node, "default", 1)
        if argument is UNPARSEABLE:
            return False
        default = GETTER_DEFAULTS[method_name]
        if argument == default:
            return True
        try:
            argument = getattr(Setting, method_name)(argument)
        except ValueError:
            return False
        return argument == default

    def is_wrong_setting_getter_call(self, node: ast.Call) -> bool:
        assert isinstance(node.func, ast.Attribute)
        method_name = node.func.attr
        if method_name not in GETTERS:
            return False
        setting_name = load_argument_from_call(node, "name", 0)
        if setting_name is UNPARSEABLE or not isinstance(setting_name, str):
            return False
        return self.is_valid_setting_getter(setting_name, method_name)

    def is_wrong_setting_subscript(self, node: ast.Subscript) -> bool:
        if not isinstance(node.slice, ast.Constant):
            return False
        setting_name = node.slice.value
        if not isinstance(setting_name, str):
            return False
        return self.is_valid_setting_getter(setting_name, "get")

    def is_valid_setting_getter(self, setting: str, getter: str) -> bool:
        if setting not in SETTINGS:
            return False
        setting_info = SETTINGS[setting]
        if setting_info.type is None:
            return False
        expected_getter = SETTING_TYPE_TO_GETTER.get(setting_info.type)
        if expected_getter is None:
            return getter != "get"
        return getter != expected_getter

    def is_settings_object(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Name):
            return node.id == "settings"
        if isinstance(node, ast.Attribute):
            return node.attr == "settings"
        return False
