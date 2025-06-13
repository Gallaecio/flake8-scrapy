from __future__ import annotations

import ast
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from packaging.utils import canonicalize_name

from . import IssueFinder
from .versions import build_package_versions_dict

if TYPE_CHECKING:
    from collections.abc import Generator

    from packaging.version import Version

MIN_VALID_SETTING_NAME_LENGTH = 3


class AllowedExcludeSettingsMixin:
    """Mixin for handling allowed and exclude settings lists."""

    def _init_allowed_exclude_settings(
        self, allowed_settings=None, exclude_settings=None
    ):
        self.allowed_settings = set(allowed_settings) if allowed_settings else set()
        self.exclude_settings = set(exclude_settings) if exclude_settings else set()


class BaseSettingsIssueFinder(IssueFinder, ABC):
    def __init__(self, filename=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.found_settings = set()
        self.filename = filename
        self.settings_methods = {
            "get": "name",
            "set": "name",
            "getbool": "name",
            "getint": "name",
            "getfloat": "name",
            "getlist": "name",
            "getdict": "name",
            "getdictorlist": "name",
            "getwithbase": "name",
            "getpriority": "name",
            "setdefault": "name",
            "delete": "name",
            "pop": "name",
        }

    @abstractmethod
    def should_report_setting(self, setting_name: str) -> bool:
        """Return True if this setting should be reported as an issue."""

    @abstractmethod
    def get_setting_message(self, setting_name: str) -> str:
        """Generate the message for this setting issue."""

    def find_issues(self, node) -> Generator[tuple[int, int, str], None, None]:
        if isinstance(node, ast.Assign):
            yield from self.check_assignment(node)
        elif isinstance(node, ast.Call):
            yield from self.check_call(node)
        elif isinstance(node, ast.Subscript):
            yield from self.check_subscript(node)
        elif isinstance(node, ast.Delete):
            yield from self.check_delete(node)
        for child in ast.iter_child_nodes(node):
            yield from self.find_issues(child)

    def check_assignment(
        self, node: ast.Assign
    ) -> Generator[tuple[int, int, str], None, None]:
        file_name = Path(self.filename).name if self.filename else None
        if file_name == "settings.py":
            for target in node.targets:
                if not isinstance(target, ast.Name) or not target.id.isupper():
                    continue
                setting_name = target.id
                if self.is_likely_setting(setting_name) and self.should_report_setting(
                    setting_name
                ):
                    yield from self.report_setting_issue(
                        node.lineno, node.col_offset, setting_name
                    )

        # Check for custom_settings assignments in any class
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "custom_settings":
                if isinstance(node.value, ast.Dict):
                    yield from self.check_dict_keys(
                        node.value, node.lineno, node.col_offset
                    )
                elif (
                    isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name)
                    and node.value.func.id == "dict"
                ):
                    yield from self.check_dict_constructor_keywords(node.value)

    def check_call(self, node: ast.Call) -> Generator[tuple[int, int, str], None, None]:  # noqa: PLR0911
        if isinstance(node.func, ast.Attribute):
            if self.is_settings_method_call(node):
                yield from self.check_settings_method_args(node)
                return
            if self.is_settings_dict_method_call(node):
                yield from self.check_settings_dict_method_args(node)
                return
            if self.is_settings_constructor_call(node):
                yield from self.check_settings_constructor_args(node)
                return
            if node.func.attr != "overridden_settings":
                return
            if (
                isinstance(node.func.value, ast.Attribute)
                and node.func.value.attr == "settings"
                and isinstance(node.func.value.value, ast.Name)
                and node.func.value.value.id == "scrapy"
            ):
                yield from self.check_overridden_settings_args(node)
                return
            if (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "settings"
            ):
                yield from self.check_overridden_settings_args(node)
            return

        if self.is_settings_constructor_call(node):
            yield from self.check_settings_constructor_args(node)
            return
        if isinstance(node.func, ast.Name) and node.func.id == "overridden_settings":
            yield from self.check_overridden_settings_args(node)

    def is_settings_constructor_call(self, node: ast.Call) -> bool:
        """Check if the call is a Settings or BaseSettings constructor."""
        if isinstance(node.func, ast.Name):
            return node.func.id in ("Settings", "BaseSettings")

        if isinstance(node.func, ast.Attribute):
            if node.func.attr not in ("Settings", "BaseSettings"):
                return False

            # Handle settings.BaseSettings
            if (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "settings"
            ):
                return True

            # Handle scrapy.settings.BaseSettings
            if (
                isinstance(node.func.value, ast.Attribute)
                and node.func.value.attr == "settings"
                and isinstance(node.func.value.value, ast.Name)
                and node.func.value.value.id == "scrapy"
            ):
                return True

        return False

    def check_subscript(
        self, node: ast.Subscript
    ) -> Generator[tuple[int, int, str], None, None]:
        if not self.is_settings_subscript(node):
            return
        if not isinstance(node.slice, ast.Constant) or not isinstance(
            node.slice.value, str
        ):
            return
        setting_name = node.slice.value
        if self.should_report_setting(setting_name):
            yield from self.report_setting_issue(
                node.slice.lineno, node.slice.col_offset, setting_name
            )

    def check_dict_keys(
        self, dict_node: ast.Dict, line: int, col: int
    ) -> Generator[tuple[int, int, str], None, None]:
        for key in dict_node.keys:
            if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                continue
            setting_name = key.value
            if setting_name.isupper() and self.should_report_setting(setting_name):
                yield from self.report_setting_issue(
                    key.lineno, key.col_offset, setting_name
                )

    def check_dict_constructor_keywords(
        self, call_node: ast.Call
    ) -> Generator[tuple[int, int, str], None, None]:
        for keyword in call_node.keywords:
            if keyword.arg is None:
                continue
            setting_name = keyword.arg
            if setting_name.isupper() and self.should_report_setting(setting_name):
                keyword_col = keyword.value.col_offset - len(setting_name) - 1
                yield from self.report_setting_issue(
                    keyword.value.lineno, keyword_col, setting_name
                )

    def is_likely_setting(self, name: str) -> bool:
        return (
            name.isupper()
            and len(name) >= MIN_VALID_SETTING_NAME_LENGTH
            and not name.startswith("_")
        )

    def is_settings_method_call(self, node: ast.Call) -> bool:
        assert isinstance(node.func, ast.Attribute)
        method_name = node.func.attr
        if method_name not in self.settings_methods:
            return False
        return self.is_settings_object(node.func.value)

    def is_settings_dict_method_call(self, node: ast.Call) -> bool:
        assert isinstance(node.func, ast.Attribute)
        method_name = node.func.attr
        dict_methods = {"setdict", "update"}
        if method_name not in dict_methods:
            return False
        return self.is_settings_object(node.func.value)

    def is_settings_subscript(self, node: ast.Subscript) -> bool:
        return self.is_settings_object(node.value)

    def is_settings_object(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Name):
            return node.id == "settings"
        if not isinstance(node, ast.Attribute):
            return False
        return node.attr == "settings"

    def check_settings_method_args(
        self, node: ast.Call
    ) -> Generator[tuple[int, int, str], None, None]:
        assert isinstance(node.func, ast.Attribute)
        method_name = node.func.attr
        param_name = self.settings_methods[method_name]
        if node.args:
            first_arg = node.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                setting_name = first_arg.value
                if self.should_report_setting(setting_name):
                    yield from self.report_setting_issue(
                        first_arg.lineno, first_arg.col_offset, setting_name
                    )
        for keyword in node.keywords:
            if keyword.arg != param_name:
                continue
            if not isinstance(keyword.value, ast.Constant) or not isinstance(
                keyword.value.value, str
            ):
                continue
            setting_name = keyword.value.value
            if self.should_report_setting(setting_name):
                yield from self.report_setting_issue(
                    keyword.value.lineno, keyword.value.col_offset, setting_name
                )

    def check_settings_dict_method_args(
        self, node: ast.Call
    ) -> Generator[tuple[int, int, str], None, None]:
        if node.args:
            first_arg = node.args[0]
            if isinstance(first_arg, ast.Dict):
                yield from self.check_dict_keys(
                    first_arg, first_arg.lineno, first_arg.col_offset
                )
            elif (
                isinstance(first_arg, ast.Call)
                and isinstance(first_arg.func, ast.Name)
                and first_arg.func.id == "dict"
            ):
                yield from self.check_dict_constructor_keywords(first_arg)
        for keyword in node.keywords:
            if keyword.arg != "values":
                continue
            if isinstance(keyword.value, ast.Dict):
                yield from self.check_dict_keys(
                    keyword.value, keyword.value.lineno, keyword.value.col_offset
                )
            elif (
                isinstance(keyword.value, ast.Call)
                and isinstance(keyword.value.func, ast.Name)
                and keyword.value.func.id == "dict"
            ):
                yield from self.check_dict_constructor_keywords(keyword.value)

    def check_settings_constructor_args(
        self, node: ast.Call
    ) -> Generator[tuple[int, int, str], None, None]:
        for arg in node.args:
            if isinstance(arg, ast.Dict):
                yield from self.check_dict_keys(arg, arg.lineno, arg.col_offset)
            elif (
                isinstance(arg, ast.Call)
                and isinstance(arg.func, ast.Name)
                and arg.func.id == "dict"
            ):
                yield from self.check_dict_constructor_keywords(arg)
        for keyword in node.keywords:
            if keyword.arg != "values":
                continue
            if isinstance(keyword.value, ast.Dict):
                yield from self.check_dict_keys(
                    keyword.value, keyword.value.lineno, keyword.value.col_offset
                )
            elif (
                isinstance(keyword.value, ast.Call)
                and isinstance(keyword.value.func, ast.Name)
                and keyword.value.func.id == "dict"
            ):
                yield from self.check_dict_constructor_keywords(keyword.value)

    def check_overridden_settings_args(
        self, node: ast.Call
    ) -> Generator[tuple[int, int, str], None, None]:
        if node.args:
            first_arg = node.args[0]
            if isinstance(first_arg, ast.Dict):
                yield from self.check_dict_keys(
                    first_arg, first_arg.lineno, first_arg.col_offset
                )
            elif (
                isinstance(first_arg, ast.Call)
                and isinstance(first_arg.func, ast.Name)
                and first_arg.func.id == "dict"
            ):
                yield from self.check_dict_constructor_keywords(first_arg)
        for keyword in node.keywords:
            if keyword.arg != "settings":
                continue
            if isinstance(keyword.value, ast.Dict):
                yield from self.check_dict_keys(
                    keyword.value, keyword.value.lineno, keyword.value.col_offset
                )
            elif (
                isinstance(keyword.value, ast.Call)
                and isinstance(keyword.value.func, ast.Name)
                and keyword.value.func.id == "dict"
            ):
                yield from self.check_dict_constructor_keywords(keyword.value)

    def check_delete(
        self, node: ast.Delete
    ) -> Generator[tuple[int, int, str], None, None]:
        for target in node.targets:
            if not isinstance(target, ast.Subscript):
                continue
            if not self.is_settings_object(target.value):
                continue
            if not isinstance(target.slice, ast.Constant) or not isinstance(
                target.slice.value, str
            ):
                continue
            setting_name = target.slice.value
            if self.should_report_setting(setting_name):
                yield from self.report_setting_issue(
                    target.slice.lineno, target.slice.col_offset, setting_name
                )

    def report_setting_issue(
        self, line: int, col: int, setting_name: str
    ) -> Generator[tuple[int, int, str], None, None]:
        if setting_name in self.found_settings:
            return
        self.found_settings.add(setting_name)

        message = self.get_setting_message(setting_name)
        yield (line, col, message)

    def get_package_version(self, package_name) -> Version | None:
        return self.package_versions.get(canonicalize_name(package_name), None)

    @property
    def package_versions(self) -> dict[str, Version]:
        if hasattr(self, "_package_versions"):
            return self._package_versions
        self._package_versions = build_package_versions_dict(self.get_project_root())
        return self._package_versions
