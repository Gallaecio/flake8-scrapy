from __future__ import annotations

import ast
import json
import re
from difflib import get_close_matches
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from . import IssueFinder
from .data import (
    HARDCODED_SUGGESTIONS,
    MIN_SCRAPY_VERSION,
    MIN_SUGGESTION_SCORE,
    SETTINGS,
    SettingType,
)
from .messaging import (
    get_enum_validation_error,
)
from .settings_base import AllowedExcludeSettingsMixin, BaseSettingsIssueFinder
from .validation import (
    is_valid_log_level,
    looks_like_callable_import_path,
    looks_like_class_import_path,
    validate_download_slots_config,
    validate_feeds_config,
    validate_periodic_log_config,
    validate_periodic_log_config_ast,
)
from .versions import (
    is_version_greater_than,
    is_version_less_than_or_equal,
)

if TYPE_CHECKING:
    from collections.abc import Generator


def get_setting_suggestions(
    unknown_setting: str, known_settings: set[str], max_suggestions: int = 3
) -> list[str]:
    hardcoded = HARDCODED_SUGGESTIONS.get(unknown_setting.upper())
    if hardcoded:
        return hardcoded[:max_suggestions]

    return get_close_matches(
        unknown_setting.upper(),
        known_settings,
        n=max_suggestions,
        cutoff=MIN_SUGGESTION_SCORE,
    )


class InvalidValueSettingsIssueFinder(
    BaseSettingsIssueFinder, AllowedExcludeSettingsMixin
):
    msg_code = "SCP18"
    msg_info = "invalid setting value"

    # Valid literal values for bool settings
    VALID_BOOL_LITERALS = (
        True,
        False,
        0,
        1,
        "True",
        "False",
        "true",
        "false",
        "0",
        "1",
    )

    # Valid types for bool settings when literal value cannot be determined
    VALID_BOOL_TYPES: ClassVar[set[type]] = {str, int, bool}

    # Valid literal values for log level settings
    VALID_LOG_LEVEL_LITERALS = (
        # String levels (case-insensitive)
        "CRITICAL",
        "FATAL",
        "ERROR",
        "WARNING",
        "WARN",
        "INFO",
        "DEBUG",
        "NOTSET",
        "critical",
        "fatal",
        "error",
        "warning",
        "warn",
        "info",
        "debug",
        "notset",
        # Standard numeric levels
        50,
        40,
        30,
        20,
        10,
        0,
    )

    def __init__(
        self,
        filename=None,
        allowed_settings=None,
        exclude_settings=None,
        *args,
        **kwargs,
    ):
        super().__init__(filename, *args, **kwargs)
        self.typed_settings = {}
        self.enum_settings = {}
        self._feeds_error_message = ""
        for name, info in SETTINGS.items():
            if info.type in (
                SettingType.BOOL,
                SettingType.INT,
                SettingType.FLOAT,
                SettingType.LIST,
                SettingType.DICT,
                SettingType.DICT_OR_LIST,
                SettingType.BASED_DICT,
                SettingType.OPT_STR,
                SettingType.STR,
                SettingType.CLS,
                SettingType.PATH,
                SettingType.OPT_PATH,
                SettingType.LOG_LEVEL,
                SettingType.ENUM_STR,
                SettingType.PERIODIC_LOG_CONFIG,
                SettingType.OPT_CALLABLE,
                SettingType.OPT_INT,
            ):
                self.typed_settings[name] = info.type
                if info.type == SettingType.ENUM_STR and info.allowed_values:
                    self.enum_settings[name] = info.allowed_values
        self._init_allowed_exclude_settings(allowed_settings, exclude_settings)
        self.validators = {
            SettingType.BOOL: lambda v: v in self.VALID_BOOL_LITERALS,
            SettingType.INT: self._can_convert_to_int,
            SettingType.FLOAT: self._can_convert_to_float,
            SettingType.LIST: self._can_convert_to_list,
            SettingType.DICT: self._can_convert_to_dict,
            SettingType.BASED_DICT: self._can_convert_to_dict,
            SettingType.DICT_OR_LIST: self._is_valid_dict_or_list_value,
            SettingType.OPT_STR: self._is_valid_optional_string,
            SettingType.STR: self._is_valid_string,
            SettingType.CLS: self._is_valid_class,
            SettingType.PATH: self._is_valid_path,
            SettingType.OPT_PATH: self._is_valid_optional_path,
            SettingType.LOG_LEVEL: is_valid_log_level,
            SettingType.ENUM_STR: self._is_valid_enum_string,
            SettingType.PERIODIC_LOG_CONFIG: validate_periodic_log_config,
            SettingType.OPT_CALLABLE: self._is_valid_optional_callable,
            SettingType.OPT_INT: self._is_valid_optional_int,
        }

        self.feeds_key_versions = {
            "batch_item_count": "2.3.0",
            "item_classes": "2.6.0",
            "item_filter": "2.6.0",
            "item_export_kwargs": "2.4.0",
            "overwrite": "2.4.0",
            "postprocessing": "2.6.0",
        }

    def should_report_setting(self, setting_name: str) -> bool:
        return (
            (
                setting_name in self.typed_settings
                or setting_name in ("USER_AGENT", "FEEDS", "DOWNLOAD_SLOTS")
            )
            and setting_name not in self.allowed_settings
            and setting_name not in self.exclude_settings
        )

    def get_setting_message(self, setting_name: str) -> str:
        if setting_name == "USER_AGENT":
            return (
                "SCP22: USER_AGENT does not seem to provide contact "
                "information. Put an URL, email address or phone number in it "
                "so that web masters of target websites may contact you."
            )

        if setting_name == "FEEDS":
            # This will be overridden by specific FEEDS error messages
            return (
                f"{self.msg_code}: {self.msg_info}: FEEDS {self._feeds_error_message}"
            )

        if setting_name == "DOWNLOAD_SLOTS":
            return f"{self.msg_code}: {self.msg_info}: DOWNLOAD_SLOTS {self._feeds_error_message}"

        setting_type = self.typed_settings[setting_name]

        type_messages = {
            SettingType.BOOL: f"only supports the following values: {', '.join(map(repr, self.VALID_BOOL_LITERALS))}.",
            SettingType.INT: "only supports values that can be passed to int()",
            SettingType.FLOAT: "only supports values that can be passed to float()",
            SettingType.LIST: "only supports values that can be passed to list()",
            SettingType.DICT: "only supports values that can be passed to dict() or strings defining a JSON object",
            SettingType.BASED_DICT: "only supports values that can be passed to dict() or strings defining a JSON object",
            SettingType.DICT_OR_LIST: "only supports None, str, tuple, dict, or list values",
            SettingType.OPT_STR: "only supports None or string values",
            SettingType.STR: "only supports string values",
            SettingType.CLS: "only supports class objects or strings containing class import paths",
            SettingType.PATH: "only supports Path objects or strings",
            SettingType.OPT_PATH: "only supports None, Path objects, or strings",
            SettingType.LOG_LEVEL: f"only supports valid logging levels: {', '.join(map(repr, self.VALID_LOG_LEVEL_LITERALS))} or any integer",
            SettingType.ENUM_STR: get_enum_validation_error(
                setting_name, self.enum_settings
            ),
            SettingType.PERIODIC_LOG_CONFIG: "only supports None, True, or a dict with 'include' and/or 'exclude' keys containing lists of strings",
            SettingType.OPT_CALLABLE: "only supports None, callable objects, or strings containing callable import paths",
            SettingType.OPT_INT: "only supports None or values that can be passed to int()",
        }

        message_suffix = type_messages.get(setting_type, "has an invalid value")
        return f"{self.msg_code}: {self.msg_info}: {setting_name} {message_suffix}"

    def check_assignment(
        self, node: ast.Assign
    ) -> Generator[tuple[int, int, str], None, None]:
        # Check direct assignments in settings.py
        file_name = Path(self.filename).name if self.filename else None
        if file_name == "settings.py":
            for target in node.targets:
                if not isinstance(target, ast.Name) or not target.id.isupper():
                    continue
                setting_name = target.id
                if self.should_report_setting(setting_name) and self._is_invalid_value(
                    node.value, setting_name
                ):
                    yield from self.report_setting_issue(
                        node.value.lineno, node.value.col_offset, setting_name
                    )

        # Check for custom_settings assignments in any class
        if isinstance(node.value, ast.Dict):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "custom_settings":
                    yield from self._check_dict_values(
                        node.value, node.lineno, node.col_offset
                    )

        # Check settings subscript assignments
        for target in node.targets:
            if (
                isinstance(target, ast.Subscript)
                and isinstance(target.ctx, ast.Store)
                and self.is_settings_subscript(target)
                and isinstance(target.slice, ast.Constant)
                and isinstance(target.slice.value, str)
            ):
                setting_name = target.slice.value
                if self.should_report_setting(setting_name) and self._is_invalid_value(
                    node.value, setting_name
                ):
                    yield from self.report_setting_issue(
                        node.value.lineno,
                        node.value.col_offset,
                        setting_name,
                    )

    def check_call(self, node: ast.Call) -> Generator[tuple[int, int, str], None, None]:  # noqa: PLR0912
        if not isinstance(node.func, ast.Attribute):
            return
        if not self.is_settings_object(node.func.value):
            return
        method_name = node.func.attr

        # Check settings.set() calls
        min_args_for_set = 2
        if method_name == "set":
            if (
                len(node.args) >= min_args_for_set
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                setting_name = node.args[0].value
                if self.should_report_setting(setting_name) and self._is_invalid_value(
                    node.args[1], setting_name
                ):
                    yield from self.report_setting_issue(
                        node.args[1].lineno,
                        node.args[1].col_offset,
                        setting_name,
                    )

            # Check keyword arguments
            for keyword in node.keywords:
                if (
                    keyword.arg == "name"
                    and isinstance(keyword.value, ast.Constant)
                    and self.should_report_setting(keyword.value.value)
                    and len(node.args) >= 1
                    and self._is_invalid_value(node.args[0], keyword.value.value)
                ):
                    setting_name = keyword.value.value
                    yield from self.report_setting_issue(
                        node.args[0].lineno,
                        node.args[0].col_offset,
                        setting_name,
                    )

        # Check settings.setdefault() calls
        elif method_name == "setdefault":
            if (
                len(node.args) >= min_args_for_set
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                setting_name = node.args[0].value
                if self.should_report_setting(setting_name) and self._is_invalid_value(
                    node.args[1], setting_name
                ):
                    yield from self.report_setting_issue(
                        node.args[1].lineno,
                        node.args[1].col_offset,
                        setting_name,
                    )

        # Check settings.setdict() calls
        elif method_name == "setdict":
            if node.args and isinstance(node.args[0], ast.Dict):
                yield from self._check_dict_values(
                    node.args[0], node.args[0].lineno, node.args[0].col_offset
                )

        # Check settings.update() calls
        elif method_name == "update":
            # Check dictionary argument
            if node.args and isinstance(node.args[0], ast.Dict):
                yield from self._check_dict_values(
                    node.args[0], node.args[0].lineno, node.args[0].col_offset
                )

            # Check keyword argument with dict value
            for keyword in node.keywords:
                if keyword.arg == "values" and isinstance(keyword.value, ast.Dict):
                    yield from self._check_dict_values(
                        keyword.value, keyword.value.lineno, keyword.value.col_offset
                    )

    def _check_dict_values(
        self, dict_node: ast.Dict, line: int, col: int
    ) -> Generator[tuple[int, int, str], None, None]:
        for key, value in zip(dict_node.keys, dict_node.values):
            if (
                isinstance(key, ast.Constant)
                and isinstance(key.value, str)
                and self.should_report_setting(key.value)
                and self._is_invalid_value(value, key.value)
            ):
                setting_name = key.value
                yield from self.report_setting_issue(
                    value.lineno, value.col_offset, setting_name
                )

    def _is_invalid_value(self, value_node: ast.AST, setting_name: str) -> bool:  # noqa: PLR0911
        if setting_name == "USER_AGENT":
            return self._is_invalid_user_agent(value_node)

        if setting_name == "FEEDS":
            feeds_error = validate_feeds_config(
                value_node, self.feeds_key_versions, self.get_package_version
            )
            if feeds_error:
                self._feeds_error_message = feeds_error
                return True
            return False

        if setting_name == "DOWNLOAD_SLOTS":
            download_slots_error = validate_download_slots_config(value_node)
            if download_slots_error:
                self._feeds_error_message = download_slots_error
                return True
            return False

        setting_type = self.typed_settings[setting_name]

        # Special handling for enum string settings
        if setting_type == SettingType.ENUM_STR:
            return self._is_invalid_enum_value(value_node, setting_name)

        # Special handling for periodic log config settings
        if setting_type == SettingType.PERIODIC_LOG_CONFIG:
            return validate_periodic_log_config_ast(value_node)

        # If we can identify the literal value
        if isinstance(value_node, ast.Constant):
            return self._is_invalid_constant_value(value_node.value, setting_type)

        # If we can identify the type but not the literal value
        if hasattr(value_node, "__class__"):
            return self._is_invalid_ast_node_type(value_node, setting_type)

        return False

    def _is_invalid_enum_value(self, value_node: ast.AST, setting_name: str) -> bool:
        if setting_name not in self.enum_settings:
            return False
        allowed_values = self.enum_settings[setting_name]
        if isinstance(value_node, ast.Constant):
            value = value_node.value
            if value is None:
                return True
            if not isinstance(value, str):
                return True
            return value not in allowed_values
        return isinstance(value_node, (ast.List, ast.Dict, ast.Set, ast.Tuple))

    def _is_invalid_constant_value(self, value, setting_type: SettingType) -> bool:
        if setting_type in self.validators:
            return not self.validators[setting_type](value)
        return False

    def _is_invalid_ast_node_type(
        self, value_node: ast.AST, setting_type: SettingType
    ) -> bool:
        complex_types = (ast.List, ast.Tuple, ast.Set, ast.Dict)
        if setting_type == SettingType.LIST:
            return False
        if setting_type in (SettingType.DICT, SettingType.BASED_DICT):
            return isinstance(value_node, (ast.List, ast.Tuple, ast.Set))
        if setting_type == SettingType.DICT_OR_LIST:
            return isinstance(value_node, ast.Set)
        if setting_type in (
            SettingType.STR,
            SettingType.OPT_STR,
            SettingType.CLS,
            SettingType.PATH,
            SettingType.OPT_PATH,
            SettingType.ENUM_STR,
            SettingType.OPT_CALLABLE,
            SettingType.OPT_INT,
        ):
            return isinstance(value_node, complex_types)
        return isinstance(value_node, complex_types)

    def _can_convert_to_int(self, value) -> bool:
        try:
            int(value)
            return True
        except (ValueError, TypeError):
            return False

    def _can_convert_to_float(self, value) -> bool:
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False

    def _can_convert_to_list(self, value) -> bool:
        try:
            list(value)
            return True
        except (ValueError, TypeError):
            return False

    def _can_convert_to_dict(self, value) -> bool:
        """Check if a value can be converted to dict or is a valid JSON object string."""
        # First try to convert to dict directly
        try:
            dict(value)
            return True
        except (ValueError, TypeError):
            pass

        # If it's a string, check if it's a valid JSON object (dict)
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return isinstance(parsed, dict)
            except (json.JSONDecodeError, ValueError):
                return False

        return False

    def _is_valid_dict_or_list_value(self, value) -> bool:
        if value is None:
            return True
        return isinstance(value, (str, tuple, dict, list))

    def _is_valid_optional_string(self, value) -> bool:
        return value is None or isinstance(value, str)

    def _is_valid_string(self, value) -> bool:
        return isinstance(value, str)

    def _is_valid_class(self, value) -> bool:
        if isinstance(value, type):
            return True
        if isinstance(value, str):
            return looks_like_class_import_path(value)
        return False

    def _is_valid_path(self, value) -> bool:
        if isinstance(value, Path):
            return True
        return isinstance(value, str)

    def _is_valid_optional_path(self, value) -> bool:
        if value is None:
            return True
        return self._is_valid_path(value)

    def _is_valid_enum_string(self, value) -> bool:
        return isinstance(value, str)

    def _is_valid_optional_callable(self, value) -> bool:
        """Check if a value is valid for OPT_CALLABLE type settings."""
        if value is None:
            return True
        if callable(value):
            return True
        if isinstance(value, str):
            return looks_like_callable_import_path(value)
        return False

    def _is_valid_optional_int(self, value) -> bool:
        """Check if a value is valid for OPT_INT type settings."""
        if value is None:
            return True
        return self._can_convert_to_int(value)

    def _is_invalid_user_agent(self, value_node: ast.AST) -> bool:
        if not isinstance(value_node, ast.Constant):
            return isinstance(
                value_node, (ast.Num, ast.List, ast.Dict, ast.Set, ast.Tuple)
            )
        value = value_node.value
        if not isinstance(value, str):
            return True
        if not value:
            return True
        if "(+http://www.yourdomain.com)" in value or "(+https://scrapy.org)" in value:
            return True
        browser_patterns = [
            r"Mozilla/\d+\.\d+",
            r"Chrome/\d+\.\d+",
            r"Safari/\d+\.\d+",
            r"Firefox/\d+\.\d+",
            r"AppleWebKit/\d+\.\d+",
            r"Gecko/\d+",
        ]
        for pattern in browser_patterns:
            if re.search(pattern, value):
                return True
        url_pattern = (
            r"https?://[a-zA-Z0-9.-]+|www\.[a-zA-Z0-9.-]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        )
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        phone_pattern = r"\b\d{3}[-.]\d{4}\b|\b\d{10,}\b|\b\(\d{3}\)\s?\d{3}[-.]\d{4}\b"
        return not (
            re.search(url_pattern, value)
            or re.search(email_pattern, value)
            or re.search(phone_pattern, value)
        )

    def check_subscript(
        self, node: ast.Subscript
    ) -> Generator[tuple[int, int, str], None, None]:
        # SCP18 only cares about assignments, not subscript reads
        # So we override this method to do nothing for subscript operations
        return
        yield  # unreachable, but needed to make this a generator


class UnknownSettingsIssueFinder(BaseSettingsIssueFinder):
    msg_code = "SCP07"
    msg_info = "unknown Scrapy setting"

    def __init__(
        self,
        filename=None,
        allowed_settings=None,
        exclude_settings=None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, filename=filename, **kwargs)
        self.known_settings = set(SETTINGS)
        if allowed_settings:
            self.known_settings.update(allowed_settings)
        self.exclude_settings = set(exclude_settings) if exclude_settings else set()

    def should_report_setting(self, setting_name: str) -> bool:
        return (
            setting_name not in self.known_settings
            and setting_name not in self.exclude_settings
        )

    def get_setting_message(self, setting_name: str) -> str:
        suggestions = get_setting_suggestions(setting_name, self.known_settings)
        message = f"{self.msg_code}: {self.msg_info}: {setting_name}"

        if not suggestions:
            return message

        if len(suggestions) == 1:
            message += f". Did you mean {suggestions[0]}?"
        else:
            suggestion_list = ", ".join(suggestions)
            message += f". Did you mean one of: {suggestion_list}?"

        return message


class DeprecatedSettingsIssueFinder(
    BaseSettingsIssueFinder, AllowedExcludeSettingsMixin
):
    msg_code = "SCP08"
    msg_info = "deprecated Scrapy setting"

    def __init__(
        self,
        filename=None,
        allowed_settings=None,
        exclude_settings=None,
        *args,
        **kwargs,
    ):
        super().__init__(filename, *args, **kwargs)
        self.deprecated_settings = self.get_deprecated_settings()
        self._init_allowed_exclude_settings(allowed_settings, exclude_settings)

    def get_deprecated_settings(self) -> set[str]:
        deprecated = set()
        for name, info in SETTINGS.items():
            package_version = self.get_package_version(info.package)
            if package_version is None:
                continue
            if info.removed_version and is_version_less_than_or_equal(
                info.removed_version, package_version
            ):
                continue
            if info.added_version and is_version_greater_than(
                info.added_version, package_version
            ):
                continue
            if info.deprecated_version and is_version_less_than_or_equal(
                info.deprecated_version, package_version
            ):
                deprecated.add(name)
        return deprecated

    def should_report_setting(self, setting_name: str) -> bool:
        return (
            setting_name in self.deprecated_settings
            and setting_name not in self.allowed_settings
            and setting_name not in self.exclude_settings
        )

    def get_setting_message(self, setting_name: str) -> str:
        setting_info = SETTINGS[setting_name]
        version = setting_info.deprecated_version
        package = setting_info.package
        if package == "scrapy" and version == MIN_SCRAPY_VERSION:
            version = f"{MIN_SCRAPY_VERSION} or earlier"
        package_name = "Scrapy" if package == "scrapy" else package
        if package == "scrapy":
            message = f"{self.msg_code}: {self.msg_info}: {setting_name} (deprecated in {package_name} {version})"
        else:
            message = f"{self.msg_code}: deprecated setting: {setting_name} (deprecated in {package_name} {version})"
        deprecation_message = setting_info.deprecation_message
        if deprecation_message:
            message += f". {deprecation_message}"
        return message


class FutureSettingsIssueFinder(BaseSettingsIssueFinder, AllowedExcludeSettingsMixin):
    msg_code = "SCP09"
    msg_info = "future Scrapy setting"

    def __init__(
        self,
        filename=None,
        allowed_settings=None,
        exclude_settings=None,
        *args,
        **kwargs,
    ):
        super().__init__(filename, *args, **kwargs)
        self.future_settings = set()
        for name, info in SETTINGS.items():
            if not info.added_version:
                continue
            package_version = self.get_package_version(info.package)
            if package_version is not None and is_version_greater_than(
                info.added_version, package_version
            ):
                self.future_settings.add(name)
        self._init_allowed_exclude_settings(allowed_settings, exclude_settings)

    def should_report_setting(self, setting_name: str) -> bool:
        return (
            setting_name in self.future_settings
            and setting_name not in self.allowed_settings
            and setting_name not in self.exclude_settings
        )

    def get_setting_message(self, setting_name: str) -> str:
        setting_info = SETTINGS[setting_name]
        version = setting_info.added_version
        package = setting_info.package
        package_name = "Scrapy" if package == "scrapy" else package
        return f"{self.msg_code}: {self.msg_info}: {setting_name} (added in {package_name} {version})"


class RemovedSettingsIssueFinder(BaseSettingsIssueFinder, AllowedExcludeSettingsMixin):
    msg_code = "SCP10"
    msg_info = "removed Scrapy setting"

    def __init__(
        self,
        filename=None,
        allowed_settings=None,
        exclude_settings=None,
        *args,
        **kwargs,
    ):
        super().__init__(filename, *args, **kwargs)
        self.removed_settings = set()
        for name, info in SETTINGS.items():
            if not info.removed_version:
                continue
            package_version = self.get_package_version(info.package)
            if package_version is not None and is_version_less_than_or_equal(
                info.removed_version, package_version
            ):
                self.removed_settings.add(name)
        self._init_allowed_exclude_settings(allowed_settings, exclude_settings)

    def should_report_setting(self, setting_name: str) -> bool:
        return (
            setting_name in self.removed_settings
            and setting_name not in self.allowed_settings
            and setting_name not in self.exclude_settings
        )

    def get_setting_message(self, setting_name: str) -> str:
        setting_info = SETTINGS[setting_name]
        version = setting_info.removed_version
        package = setting_info.package
        package_name = "Scrapy" if package == "scrapy" else package
        return f"{self.msg_code}: {self.msg_info}: {setting_name} (removed in {package_name} {version})"


class MissingPackageSettingsIssueFinder(
    BaseSettingsIssueFinder, AllowedExcludeSettingsMixin
):
    msg_code = "SCP15"
    msg_info = "setting for package not in requirements.txt"

    def __init__(self, filename=None, allowed_settings=None, *args, **kwargs):
        super().__init__(filename, *args, **kwargs)
        self.missing_package_settings = set()
        for name, info in SETTINGS.items():
            if (
                info.package != "scrapy"
                and self.get_package_version(info.package) is None
            ):
                self.missing_package_settings.add(name)
        self._init_allowed_exclude_settings(allowed_settings)

    def should_report_setting(self, setting_name: str) -> bool:
        return (
            setting_name in self.missing_package_settings
            and setting_name not in self.allowed_settings
        )

    def get_setting_message(self, setting_name: str) -> str:
        setting_info = SETTINGS[setting_name]
        package = setting_info.package
        return f"{self.msg_code}: {self.msg_info}: {setting_name} (package: {package})"


class TypeMismatchSettingsIssueFinder(
    BaseSettingsIssueFinder, AllowedExcludeSettingsMixin
):
    msg_code = "SCP17"
    msg_info = "wrong setting getter"

    TYPE_TO_METHOD: ClassVar[dict[SettingType, str]] = {
        SettingType.BOOL: "getbool",
        SettingType.INT: "getint",
        SettingType.FLOAT: "getfloat",
        SettingType.LIST: "getlist",
        SettingType.DICT: "getdict",
        SettingType.DICT_OR_LIST: "getdictorlist",
        SettingType.BASED_DICT: "getwithbase",
    }

    def __init__(
        self,
        filename=None,
        allowed_settings=None,
        exclude_settings=None,
        *args,
        **kwargs,
    ):
        super().__init__(filename, *args, **kwargs)
        self.typed_settings = {}
        for name, info in SETTINGS.items():
            if info.type is not None:
                self.typed_settings[name] = info.type
        self._init_allowed_exclude_settings(allowed_settings, exclude_settings)

    def should_report_setting(self, setting_name: str) -> bool:
        return (
            setting_name in self.typed_settings
            and setting_name not in self.allowed_settings
            and setting_name not in self.exclude_settings
        )

    def get_setting_message(self, setting_name: str) -> str:
        setting_type = self.typed_settings[setting_name]
        expected_method = self.TYPE_TO_METHOD.get(setting_type, "get")
        if expected_method == "get":
            return f"{self.msg_code}: {self.msg_info}: use [] or get() to read {setting_name}"
        return f"{self.msg_code}: {self.msg_info}: use {expected_method}() to read {setting_name}"

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
                if (
                    self.should_report_setting(setting_name)
                    and setting_name in self.typed_settings
                ):
                    setting_type = self.typed_settings[setting_name]
                    expected_method = self.TYPE_TO_METHOD.get(setting_type, "get")
                    if method_name != expected_method:
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
            if (
                self.should_report_setting(setting_name)
                and setting_name in self.typed_settings
            ):
                setting_type = self.typed_settings[setting_name]
                expected_method = self.TYPE_TO_METHOD.get(setting_type, "get")
                if method_name != expected_method:
                    yield from self.report_setting_issue(
                        keyword.value.lineno, keyword.value.col_offset, setting_name
                    )

    def check_assignment(
        self, node: ast.Assign
    ) -> Generator[tuple[int, int, str], None, None]:
        # SCP17 only cares about reading settings, not assignments
        # So we override this method to do nothing for assignment operations
        return
        yield  # unreachable, but needed to make this a generator

    def check_call(self, node: ast.Call) -> Generator[tuple[int, int, str], None, None]:
        if not isinstance(node.func, ast.Attribute):
            return
        if not self.is_settings_object(node.func.value):
            return

        method_name = node.func.attr

        # Only check getter methods, not setter methods
        getter_methods = {
            "get",
            "getbool",
            "getint",
            "getfloat",
            "getlist",
            "getdict",
            "getdictorlist",
            "getwithbase",
            "getpriority",
        }

        if method_name not in getter_methods:
            return

        # Use the original settings method checking logic
        if self.is_settings_method_call(node):
            yield from self.check_settings_method_args(node)

    def check_subscript(
        self, node: ast.Subscript
    ) -> Generator[tuple[int, int, str], None, None]:
        if not isinstance(node.ctx, ast.Load):
            return
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


class MissingUserAgentIssueFinder(IssueFinder):
    msg_code = "SCP19"
    msg_info = "no USER_AGENT"

    def __init__(self, filename=None, *args, **kwargs):
        super().__init__(filename, *args, **kwargs)
        self.found_user_agent = False

    def find_issues(self, node) -> Generator[tuple[int, int, str], None, None]:
        if not self.file_is_settings_module():
            return

        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "USER_AGENT":
                    self.found_user_agent = True

        if isinstance(node, ast.Module):
            # Traverse all child nodes first to check for USER_AGENT
            for child in ast.walk(node):
                if isinstance(child, ast.Assign):
                    for target in child.targets:
                        if isinstance(target, ast.Name) and target.id == "USER_AGENT":
                            self.found_user_agent = True
                            break

            if not self.found_user_agent:
                yield (1, 0, f"{self.msg_code} {self.msg_info}")


class RobotsTxtObeyIssueFinder(IssueFinder):
    msg_code = "SCP20"
    msg_info = "ROBOTSTXT_OBEY not enabled"

    def __init__(self, filename=None, *args, **kwargs):
        super().__init__(filename, *args, **kwargs)
        self.found_robotstxt_obey = False
        self.robotstxt_obey_enabled = False

    def find_issues(self, node) -> Generator[tuple[int, int, str], None, None]:
        if not self.file_is_settings_module():
            return

        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "ROBOTSTXT_OBEY":
                    self.found_robotstxt_obey = True
                    if (
                        isinstance(node.value, ast.Constant)
                        and node.value.value is True
                    ):
                        self.robotstxt_obey_enabled = True

        if isinstance(node, ast.Module):
            for child in ast.walk(node):
                if isinstance(child, ast.Assign):
                    for target in child.targets:
                        if (
                            isinstance(target, ast.Name)
                            and target.id == "ROBOTSTXT_OBEY"
                        ):
                            self.found_robotstxt_obey = True
                            if (
                                isinstance(child.value, ast.Constant)
                                and child.value.value is True
                            ):
                                self.robotstxt_obey_enabled = True
                            break

            if not self.found_robotstxt_obey or not self.robotstxt_obey_enabled:
                yield (1, 0, f"{self.msg_code} {self.msg_info}")


class ThrottlingConfigIssueFinder(IssueFinder):
    msg_code = "SCP21"
    msg_info = "incomplete throttling config"

    def __init__(self, filename):
        self.filename = filename

    def find_issues(self, node):  # noqa: PLR0912
        if not self.file_is_settings_module():
            return

        if not isinstance(node, ast.Module):
            return

        autothrottle_enabled = False
        found_settings = set()
        required_settings = {
            "CONCURRENT_REQUESTS",
            "CONCURRENT_REQUESTS_PER_DOMAIN",
            "DOWNLOAD_DELAY",
        }

        for child in ast.walk(node):
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        if target.id == "AUTOTHROTTLE_ENABLED":
                            if (
                                isinstance(child.value, ast.Constant)
                                and child.value.value is True
                            ):
                                autothrottle_enabled = True
                        elif target.id in required_settings:
                            found_settings.add(target.id)
            elif (
                isinstance(child, ast.Subscript)
                and isinstance(child.value, ast.Name)
                and child.value.id == "settings"
                and isinstance(child.slice, ast.Constant)
                and isinstance(child.slice.value, str)
            ):
                setting_name = child.slice.value
                if setting_name == "AUTOTHROTTLE_ENABLED":
                    parent = getattr(child, "parent", None)
                    if (
                        isinstance(parent, ast.Assign)
                        and isinstance(parent.value, ast.Constant)
                        and parent.value.value is True
                    ):
                        autothrottle_enabled = True
                elif setting_name in required_settings:
                    found_settings.add(setting_name)

        if not autothrottle_enabled and found_settings != required_settings:
            missing_settings = required_settings - found_settings
            if missing_settings:
                yield (1, 0, f"{self.msg_code} {self.msg_info}")


DEFAULT_SETTINGS = {
    "ADDONS",
    "AJAXCRAWL_ENABLED",
    "ASYNCIO_EVENT_LOOP",
    "AUTOTHROTTLE_DEBUG",
    "AUTOTHROTTLE_ENABLED",
    "AUTOTHROTTLE_MAX_DELAY",
    "AUTOTHROTTLE_START_DELAY",
    "AUTOTHROTTLE_TARGET_CONCURRENCY",
    "BOT_NAME",
    "CLOSESPIDER_ERRORCOUNT",
    "CLOSESPIDER_ITEMCOUNT",
    "CLOSESPIDER_PAGECOUNT",
    "CLOSESPIDER_TIMEOUT",
    "COMMANDS_MODULE",
    "COMPRESSION_ENABLED",
    "CONCURRENT_ITEMS",
    "CONCURRENT_REQUESTS",
    "CONCURRENT_REQUESTS_PER_DOMAIN",
    "CONCURRENT_REQUESTS_PER_IP",
    "COOKIES_DEBUG",
    "COOKIES_ENABLED",
    "DEFAULT_DROPITEM_LOG_LEVEL",
    "DEFAULT_ITEM_CLASS",
    "DEFAULT_REQUEST_HEADERS",
    "DEPTH_LIMIT",
    "DEPTH_PRIORITY",
    "DEPTH_STATS_VERBOSE",
    "DNSCACHE_ENABLED",
    "DNSCACHE_SIZE",
    "DNS_RESOLVER",
    "DNS_TIMEOUT",
    "DOWNLOAD_DELAY",
    "DOWNLOADER",
    "DOWNLOADER_CLIENTCONTEXTFACTORY",
    "DOWNLOADER_CLIENT_TLS_CIPHERS",
    "DOWNLOADER_CLIENT_TLS_METHOD",
    "DOWNLOADER_CLIENT_TLS_VERBOSE_LOGGING",
    "DOWNLOADER_HTTPCLIENTFACTORY",
    "DOWNLOADER_MIDDLEWARES",
    "DOWNLOADER_MIDDLEWARES_BASE",
    "DOWNLOADER_STATS",
    "DOWNLOAD_FAIL_ON_DATALOSS",
    "DOWNLOAD_HANDLERS",
    "DOWNLOAD_HANDLERS_BASE",
    "DOWNLOAD_MAXSIZE",
    "DOWNLOAD_TIMEOUT",
    "DOWNLOAD_WARNSIZE",
    "DUPEFILTER_CLASS",
    "EDITOR",
    "EXTENSIONS",
    "EXTENSIONS_BASE",
    "FEED_EXPORT_BATCH_ITEM_COUNT",
    "FEED_EXPORT_ENCODING",
    "FEED_EXPORTERS",
    "FEED_EXPORTERS_BASE",
    "FEED_EXPORT_FIELDS",
    "FEED_EXPORT_INDENT",
    "FEEDS",
    "FEED_STORAGE_FTP_ACTIVE",
    "FEED_STORAGE_GCS_ACL",
    "FEED_STORAGES",
    "FEED_STORAGES_BASE",
    "FEED_STORE_EMPTY",
    "FEED_TEMPDIR",
    "FEED_URI_PARAMS",
    "FILES_STORE_GCS_ACL",
    "FORCE_CRAWLER_PROCESS",
    "FTP_PASSIVE_MODE",
    "FTP_PASSWORD",
    "FTP_USER",
    "GCS_PROJECT_ID",
    "HTTPCACHE_ALWAYS_STORE",
    "HTTPCACHE_DBM_MODULE",
    "HTTPCACHE_DIR",
    "HTTPCACHE_ENABLED",
    "HTTPCACHE_EXPIRATION_SECS",
    "HTTPCACHE_GZIP",
    "HTTPCACHE_IGNORE_HTTP_CODES",
    "HTTPCACHE_IGNORE_MISSING",
    "HTTPCACHE_IGNORE_RESPONSE_CACHE_CONTROLS",
    "HTTPCACHE_IGNORE_SCHEMES",
    "HTTPCACHE_POLICY",
    "HTTPCACHE_STORAGE",
    "HTTPPROXY_AUTH_ENCODING",
    "HTTPPROXY_ENABLED",
    "IMAGES_STORE_GCS_ACL",
    "ITEM_PIPELINES",
    "ITEM_PIPELINES_BASE",
    "ITEM_PROCESSOR",
    "JOBDIR",
    "LOG_DATEFORMAT",
    "LOG_ENABLED",
    "LOG_ENCODING",
    "LOG_FILE",
    "LOG_FILE_APPEND",
    "LOG_FORMAT",
    "LOG_FORMATTER",
    "LOG_LEVEL",
    "LOG_SHORT_NAMES",
    "LOGSTATS_INTERVAL",
    "LOG_STDOUT",
    "LOG_VERSIONS",
    "MAIL_FROM",
    "MAIL_HOST",
    "MAIL_PASS",
    "MAIL_PORT",
    "MAIL_USER",
    "MEMDEBUG_ENABLED",
    "MEMDEBUG_NOTIFY",
    "MEMUSAGE_CHECK_INTERVAL_SECONDS",
    "MEMUSAGE_ENABLED",
    "MEMUSAGE_LIMIT_MB",
    "MEMUSAGE_NOTIFY_MAIL",
    "MEMUSAGE_WARNING_MB",
    "METAREFRESH_ENABLED",
    "METAREFRESH_IGNORE_TAGS",
    "METAREFRESH_MAXDELAY",
    "NEWSPIDER_MODULE",
    "PERIODIC_LOG_DELTA",
    "PERIODIC_LOG_STATS",
    "PERIODIC_LOG_TIMING_ENABLED",
    "RANDOMIZE_DOWNLOAD_DELAY",
    "REACTOR_THREADPOOL_MAXSIZE",
    "REDIRECT_ENABLED",
    "REDIRECT_MAX_TIMES",
    "REDIRECT_PRIORITY_ADJUST",
    "REFERER_ENABLED",
    "REFERRER_POLICY",
    "REQUEST_FINGERPRINTER_CLASS",
    "REQUEST_FINGERPRINTER_IMPLEMENTATION",
    "RETRY_ENABLED",
    "RETRY_EXCEPTIONS",
    "RETRY_HTTP_CODES",
    "RETRY_PRIORITY_ADJUST",
    "RETRY_TIMES",
    "ROBOTSTXT_OBEY",
    "ROBOTSTXT_PARSER",
    "ROBOTSTXT_USER_AGENT",
    "SCHEDULER",
    "SCHEDULER_DEBUG",
    "SCHEDULER_DISK_QUEUE",
    "SCHEDULER_MEMORY_QUEUE",
    "SCHEDULER_PRIORITY_QUEUE",
    "SCHEDULER_START_DISK_QUEUE",
    "SCHEDULER_START_MEMORY_QUEUE",
    "SCRAPER_SLOT_MAX_ACTIVE_SIZE",
    "SPIDER_CONTRACTS",
    "SPIDER_CONTRACTS_BASE",
    "SPIDER_LOADER_CLASS",
    "SPIDER_LOADER_WARN_ONLY",
    "SPIDER_MIDDLEWARES",
    "SPIDER_MIDDLEWARES_BASE",
    "SPIDER_MODULES",
    "STATS_CLASS",
    "STATS_DUMP",
    "STATSMAILER_RCPTS",
    "TELNETCONSOLE_ENABLED",
    "TELNETCONSOLE_HOST",
    "TELNETCONSOLE_PASSWORD",
    "TELNETCONSOLE_PORT",
    "TELNETCONSOLE_USERNAME",
    "TEMPLATES_DIR",
    "TWISTED_REACTOR",
    "URLLENGTH_LIMIT",
    "USER_AGENT",
    "WARN_ON_GENERATOR_RETURN_VALUE",
}

DEFAULT_SETTINGS_WITH_NONE = {
    "FEED_EXPORT_ENCODING",
    "FEED_EXPORT_FIELDS",
    "FEED_TEMPDIR",
    "FEED_URI_PARAMS",
    "JOBDIR",
    "LOG_FILE",
    "MAIL_USER",
    "MAIL_PASS",
    "PERIODIC_LOG_DELTA",
    "PERIODIC_LOG_STATS",
    "ROBOTSTXT_USER_AGENT",
    "TELNETCONSOLE_PASSWORD",
}


class UnnecessaryGetIssueFinder(BaseSettingsIssueFinder):
    msg_code = "SCP25"
    msg_info = "unneeded get()"

    def __init__(self, filename=None, *args, **kwargs):
        super().__init__(filename, *args, **kwargs)

    def should_report_setting(self, setting_name: str) -> bool:
        # Only report if it's a known setting and doesn't have a specific typed getter (to avoid conflicts with SCP17)
        if setting_name not in SETTINGS:
            return False
        setting_info = SETTINGS[setting_name]
        if setting_info.type is not None:
            # Check if this type has a specific getter method defined in SCP17
            type_to_method = {
                SettingType.BOOL: "getbool",
                SettingType.INT: "getint",
                SettingType.FLOAT: "getfloat",
                SettingType.LIST: "getlist",
                SettingType.DICT: "getdict",
                SettingType.DICT_OR_LIST: "getdictorlist",
                SettingType.BASED_DICT: "getwithbase",
            }
            # Only report if the type doesn't have a specific getter (i.e., uses "get")
            return setting_info.type not in type_to_method
        return True

    def get_setting_message(self, setting_name: str) -> str:
        return f"{self.msg_code}: {self.msg_info}: use [] instead of get() to read {setting_name}"

    def check_assignment(
        self, node: ast.Assign
    ) -> Generator[tuple[int, int, str], None, None]:
        return
        yield  # pragma: no cover

    def check_call(self, node: ast.Call) -> Generator[tuple[int, int, str], None, None]:
        if not isinstance(node.func, ast.Attribute):
            return

        # Only check get() calls for SCP25, not typed getters (those are handled by SCP17)
        if self.is_settings_method_call(node) and node.func.attr == "get":
            yield from self.check_settings_method_args(node)

    def check_subscript(
        self, node: ast.Subscript
    ) -> Generator[tuple[int, int, str], None, None]:
        return
        yield  # pragma: no cover

    def check_delete(
        self, node: ast.Delete
    ) -> Generator[tuple[int, int, str], None, None]:
        return
        yield  # pragma: no cover

    def check_settings_method_args(
        self, node: ast.Call
    ) -> Generator[tuple[int, int, str], None, None]:
        assert isinstance(node.func, ast.Attribute)
        method_name = node.func.attr

        # Only handle get() calls for SCP25
        if method_name != "get":
            return

        first_arg = node.args[0] if node.args else None
        if (
            first_arg
            and isinstance(first_arg, ast.Constant)
            and isinstance(first_arg.value, str)
        ):
            MAX_ARGS_WITH_DEFAULT = 2
            first_arg = node.args[0] if node.args else None
            if (
                first_arg
                and isinstance(first_arg, ast.Constant)
                and isinstance(first_arg.value, str)
            ):
                setting_name = first_arg.value
                # Check if it's unneeded: no default or default is None
                if self.should_report_setting(setting_name) and (
                    len(node.args) == 1
                    or (
                        len(node.args) == MAX_ARGS_WITH_DEFAULT
                        and isinstance(node.args[1], ast.Constant)
                        and node.args[1].value is None
                    )
                ):
                    yield from self.report_setting_issue(
                        first_arg.lineno, first_arg.col_offset, setting_name
                    )

        # Check keyword arguments
        for keyword in node.keywords:
            if (
                keyword.arg == "name"
                and isinstance(keyword.value, ast.Constant)
                and isinstance(keyword.value.value, str)
            ):
                setting_name = keyword.value.value
                if self.should_report_setting(setting_name):
                    # Check if default is None or not provided
                    has_none_default = False
                    for kw in node.keywords:
                        if (
                            kw.arg == "default"
                            and isinstance(kw.value, ast.Constant)
                            and kw.value.value is None
                        ):
                            has_none_default = True
                            break

                    if (
                        not any(kw.arg == "default" for kw in node.keywords)
                        or has_none_default
                    ):
                        yield from self.report_setting_issue(
                            keyword.value.lineno, keyword.value.col_offset, setting_name
                        )


class IgnoredGetDefaultIssueFinder(BaseSettingsIssueFinder):
    msg_code = "SCP26"
    msg_info = "ignored getter default"

    def __init__(self, filename=None, *args, **kwargs):
        super().__init__(filename, *args, **kwargs)

    def should_report_setting(self, setting_name: str) -> bool:
        return setting_name in SETTINGS

    def get_setting_message(self, setting_name: str, method_name: str = "get") -> str:
        return (
            f"{self.msg_code}: {self.msg_info}: {setting_name} is set in "
            "scrapy.settings.default_settings with a non-None value, "
            f"so the default value passed to {method_name}() will never be used."
        )

    def check_assignment(
        self, node: ast.Assign
    ) -> Generator[tuple[int, int, str], None, None]:
        return
        yield  # pragma: no cover

    def check_call(self, node: ast.Call) -> Generator[tuple[int, int, str], None, None]:
        if not isinstance(node.func, ast.Attribute):
            return

        getter_methods = {
            "get",
            "getbool",
            "getint",
            "getfloat",
            "getlist",
            "getdict",
            "getdictorlist",
            "getwithbase",
        }

        if self.is_settings_method_call(node) and node.func.attr in getter_methods:
            yield from self.check_settings_method_args(node)

    def check_subscript(
        self, node: ast.Subscript
    ) -> Generator[tuple[int, int, str], None, None]:
        return
        yield  # pragma: no cover

    def check_delete(
        self, node: ast.Delete
    ) -> Generator[tuple[int, int, str], None, None]:
        return
        yield  # pragma: no cover

    def check_settings_method_args(
        self, node: ast.Call
    ) -> Generator[tuple[int, int, str], None, None]:
        assert isinstance(node.func, ast.Attribute)
        method_name = node.func.attr
        getter_methods = {
            "get",
            "getbool",
            "getint",
            "getfloat",
            "getlist",
            "getdict",
            "getdictorlist",
            "getwithbase",
        }

        if method_name not in getter_methods:
            return

        first_arg = node.args[0] if node.args else None
        if (
            first_arg
            and isinstance(first_arg, ast.Constant)
            and isinstance(first_arg.value, str)
        ):
            MAX_ARGS_WITH_DEFAULT = 2
            first_arg = node.args[0] if node.args else None
            if (
                first_arg
                and isinstance(first_arg, ast.Constant)
                and isinstance(first_arg.value, str)
            ):
                setting_name = first_arg.value
                if (
                    self.should_report_setting(setting_name)
                    and setting_name in DEFAULT_SETTINGS
                    and setting_name not in DEFAULT_SETTINGS_WITH_NONE
                    and len(node.args) == MAX_ARGS_WITH_DEFAULT
                    and not (
                        isinstance(node.args[1], ast.Constant)
                        and node.args[1].value is None
                    )
                ):
                    # Point to the default value (second argument) instead of setting name
                    default_arg = node.args[1]
                    if setting_name in self.found_settings:
                        return
                    self.found_settings.add(setting_name)
                    message = self.get_setting_message(setting_name, method_name)
                    yield (default_arg.lineno, default_arg.col_offset, message)

        # Check keyword arguments
        for keyword in node.keywords:
            if (
                keyword.arg == "name"
                and isinstance(keyword.value, ast.Constant)
                and isinstance(keyword.value.value, str)
            ):
                setting_name = keyword.value.value
                if (
                    self.should_report_setting(setting_name)
                    and setting_name in DEFAULT_SETTINGS
                    and setting_name not in DEFAULT_SETTINGS_WITH_NONE
                ):
                    # Check if there's a non-None default in keywords
                    for kw in node.keywords:
                        if kw.arg == "default" and not (
                            isinstance(kw.value, ast.Constant)
                            and kw.value.value is None
                        ):
                            if setting_name in self.found_settings:
                                return
                            self.found_settings.add(setting_name)
                            message = self.get_setting_message(
                                setting_name, method_name
                            )
                            yield (kw.value.lineno, kw.value.col_offset, message)
                            break


class DuplicateSettingsIssueFinder:
    msg_code = "SCP23"

    def __init__(self, filename):
        self.filename = filename

    def find_issues(self, node):
        if not (self.filename and self.filename.endswith("settings.py")):
            return

        if not isinstance(node, ast.Module):
            return

        seen_settings = {}

        for child in node.body:
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        setting_name = target.id
                        if setting_name in seen_settings:
                            yield (
                                child.lineno,
                                child.col_offset,
                                f"{self.msg_code}: {setting_name} is set multiple times in settings.py",
                            )
                        else:
                            seen_settings[setting_name] = child.lineno


class BaseSettingNameIssueFinder(BaseSettingsIssueFinder):
    msg_code = "SCP24"
    msg_info = "use of BASE setting"

    def __init__(self, filename=None, *args, **kwargs):
        super().__init__(filename, *args, **kwargs)

    def should_report_setting(self, setting_name: str) -> bool:
        return setting_name.endswith("_BASE") and setting_name in SETTINGS

    def get_setting_message(self, setting_name: str) -> str:
        return f"{self.msg_code}: {self.msg_info}: do not use {setting_name}, use {setting_name[:-5]} instead"


class ImportPathStringIssueFinder(BaseSettingsIssueFinder):
    msg_code = "SCP27"
    msg_info = "import path string in setting"
    _instance_count = 0

    def __init__(self, filename=None, *args, **kwargs):
        super().__init__(filename, *args, **kwargs)
        ImportPathStringIssueFinder._instance_count += 1

    def should_report_setting(self, setting_name: str) -> bool:
        # Always return False here to prevent base class from reporting
        # We handle the logic in our specific check methods
        return False

    def get_setting_message(self, setting_name: str) -> str:
        return f"{self.msg_code}: {self.msg_info}: {setting_name} should import the class directly instead of using import path string"

    def _should_report_cls_setting(self, setting_name: str) -> bool:
        return (
            setting_name in SETTINGS and SETTINGS[setting_name].type == SettingType.CLS
        )

    def check_assignment(
        self, node: ast.Assign
    ) -> Generator[tuple[int, int, str], None, None]:
        # Add a guard to prevent duplicate processing
        if hasattr(node, "_scp27_processed"):
            return
        node._scp27_processed = True

        file_name = Path(self.filename).name if self.filename else None
        # Check both settings.py files and any file (for subscript assignments)
        for target in node.targets:
            setting_name = None

            # Handle direct assignment: SETTING = "value"
            if isinstance(target, ast.Name) and self.is_likely_setting(target.id):
                if (
                    file_name == "settings.py"
                ):  # Only check direct assignments in settings.py
                    setting_name = target.id

            # Handle subscript assignment: settings["SETTING"] = "value"
            elif (
                isinstance(target, ast.Subscript)
                and self.is_settings_subscript(target)
                and isinstance(target.slice, ast.Constant)
                and isinstance(target.slice.value, str)
            ):
                setting_name = target.slice.value

            if (
                setting_name
                and self._should_report_cls_setting(setting_name)
                and self._is_import_path_string_value(node.value)
            ):
                yield (
                    node.value.lineno,
                    node.value.col_offset,
                    self.get_setting_message(setting_name),
                )

        # Handle custom_settings assignments like the base class does
        if isinstance(node.value, ast.Dict):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "custom_settings":
                    yield from self._check_dict_values(node.value)

    def check_call(self, node: ast.Call) -> Generator[tuple[int, int, str], None, None]:
        if isinstance(node.func, ast.Attribute) and self.is_settings_method_call(node):
            yield from self.check_settings_method_args(node)
        elif isinstance(node.func, ast.Attribute) and self.is_settings_dict_method_call(
            node
        ):
            yield from self.check_settings_dict_method_args(node)
        elif self.is_settings_constructor_call(node):
            yield from self.check_settings_constructor_args(node)
        elif self.is_overridden_settings_call(node):
            yield from self.check_overridden_settings_args(node)

    def is_settings_constructor_call(self, node: ast.Call) -> bool:
        if isinstance(node.func, ast.Name):
            return node.func.id in ("Settings", "BaseSettings")
        return False

    def is_overridden_settings_call(self, node: ast.Call) -> bool:
        if isinstance(node.func, ast.Name):
            return node.func.id == "overridden_settings"
        if isinstance(node.func, ast.Attribute):
            return node.func.attr == "overridden_settings"
        return False

    def check_subscript(
        self, node: ast.Subscript
    ) -> Generator[tuple[int, int, str], None, None]:
        # SCP27 doesn't need to check subscript reads, only assignments
        # Subscript assignments are handled by the framework differently
        return
        yield  # unreachable, but needed to make this a generator

    def check_settings_method_args(
        self, node: ast.Call
    ) -> Generator[tuple[int, int, str], None, None]:
        if not node.args:
            return

        first_arg = node.args[0]
        if not (
            isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str)
        ):
            return

        setting_name = first_arg.value
        if not self._should_report_cls_setting(setting_name):
            return

        if len(node.args) >= 2:  # noqa: PLR2004
            value = node.args[1]
            if self._is_import_path_string_value(value):
                yield (
                    value.lineno,
                    value.col_offset,
                    self.get_setting_message(setting_name),
                )

    def check_settings_dict_method_args(
        self, node: ast.Call
    ) -> Generator[tuple[int, int, str], None, None]:
        method_name = node.func.attr
        if method_name == "update":
            for arg in node.args:
                if isinstance(arg, ast.Dict):
                    yield from self._check_dict_values(arg)

        for keyword in node.keywords:
            if keyword.arg == "values" and isinstance(keyword.value, ast.Dict):
                yield from self._check_dict_values(keyword.value)

    def check_settings_constructor_args(
        self, node: ast.Call
    ) -> Generator[tuple[int, int, str], None, None]:
        for arg in node.args:
            if isinstance(arg, ast.Dict):
                yield from self._check_dict_values(arg)

        for keyword in node.keywords:
            if keyword.arg == "values" and isinstance(keyword.value, ast.Dict):
                yield from self._check_dict_values(keyword.value)

    def check_overridden_settings_args(
        self, node: ast.Call
    ) -> Generator[tuple[int, int, str], None, None]:
        for arg in node.args:
            if isinstance(arg, ast.Dict):
                yield from self._check_dict_values(arg)

    def _check_dict_values(
        self, node: ast.Dict
    ) -> Generator[tuple[int, int, str], None, None]:
        for key, value in zip(node.keys, node.values):
            if (
                isinstance(key, ast.Constant)
                and isinstance(key.value, str)
                and self._should_report_cls_setting(key.value)
            ):
                setting_name = key.value
                if self._is_import_path_string_value(value):
                    yield (
                        value.lineno,
                        value.col_offset,
                        self.get_setting_message(setting_name),
                    )

    def _is_import_path_string_value(self, value: ast.AST) -> bool:
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            return looks_like_class_import_path(value.value)
        return False
