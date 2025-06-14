from __future__ import annotations

import ast
import json
import re
from difflib import get_close_matches
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flake8_scrapy.config import Config

from .data import (
    DEFAULT_SETTINGS,
    HARDCODED_SUGGESTIONS,
    MIN_SUGGESTION_SCORE,
    SETTINGS,
    SettingType,
)
from .messaging import (
    Issue,
)
from .validation import (
    looks_like_callable_import_path,
    looks_like_class_import_path,
    validate_download_slots_config,
    validate_feeds_config,
    validate_periodic_log_config_ast,
)
from .versions import (
    build_package_versions_dict,
    is_version_greater_than,
    is_version_less_than_or_equal,
)

if TYPE_CHECKING:
    from packaging.version import Version

from packaging.utils import canonicalize_name


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


def get_setting_value_issues(  # noqa: PLR0912, PLR0915
    setting: str, value: ast.expr, config: Config
) -> list[Issue]:
    """Report issues based on setting name and value AST node.

    This function checks for:
    - SCP18: Invalid setting value
    - SCP27: Unneeded import path string
    """
    issues = []

    if setting not in SETTINGS:
        return issues

    setting_info = SETTINGS[setting]
    setting_type = setting_info.type

    # Check for invalid values (SCP18)
    is_invalid = False
    if setting == "FEEDS":
        is_invalid = bool(validate_feeds_config(value, config))
    elif setting == "DOWNLOAD_SLOTS":
        is_invalid = bool(validate_download_slots_config(value))
    elif setting_type == SettingType.BOOL:
        is_invalid = _is_invalid_bool_value_standalone(value)
    elif setting_type == SettingType.INT:
        is_invalid = _is_invalid_int_value_standalone(value)
    elif setting_type == SettingType.FLOAT:
        is_invalid = _is_invalid_float_value_standalone(value)
    elif setting_type == SettingType.LIST:
        is_invalid = _is_invalid_list_value_standalone(value)
    elif setting_type in {SettingType.DICT, SettingType.BASED_DICT}:
        is_invalid = _is_invalid_dict_value_standalone(value)
    elif setting_type == SettingType.DICT_OR_LIST:
        is_invalid = _is_invalid_dict_or_list_value_standalone(value)
    elif setting_type == SettingType.ENUM_STR:
        is_invalid = _is_invalid_enum_str_value_standalone(setting, value)
    elif setting_type == SettingType.PERIODIC_LOG_CONFIG:
        is_invalid = _is_invalid_periodic_log_config_value_standalone(value)
    elif setting_type == SettingType.LOG_LEVEL:
        is_invalid = _is_invalid_log_level_value_standalone(value)
    elif setting_type == SettingType.PATH:
        is_invalid = _is_invalid_path_value_standalone(value)
    elif setting_type == SettingType.OPT_PATH:
        is_invalid = _is_invalid_optional_path_value_standalone(value)
    elif setting_type == SettingType.OPT_STR:
        is_invalid = _is_invalid_optional_string_value_standalone(value)
    elif setting_type == SettingType.STR:
        is_invalid = _is_invalid_string_value_standalone(value)
    elif setting_type == SettingType.CLS:
        is_invalid = _is_invalid_class_value_standalone(value)
    elif setting_type == SettingType.OPT_CALLABLE:
        is_invalid = _is_invalid_optional_callable_value_standalone(value)
    elif setting_type == SettingType.OPT_INT:
        is_invalid = _is_invalid_optional_int_value_standalone(value)

    if is_invalid:
        value_col = getattr(value, "col_offset", 0)
        value_line = getattr(value, "lineno", 1)
        issues.append(
            Issue(18, "invalid setting value", line=value_line, column=value_col)
        )

    # Check for USER_AGENT without contact info (SCP22)
    if setting == "USER_AGENT" and _is_invalid_user_agent_standalone(value):
        value_col = getattr(value, "col_offset", 0)
        value_line = getattr(value, "lineno", 1)
        issues.append(Issue(22, "no contact info", line=value_line, column=value_col))

    # Check for import path strings (SCP27)
    if (
        setting_type == SettingType.CLS
        and isinstance(value, ast.Constant)
        and isinstance(value.value, str)
        and looks_like_class_import_path(value.value)
    ):
        issues.append(
            Issue(
                27,
                "unneeded import path string",
                column=value.col_offset,
                line=value.lineno,
            )
        )

    return issues


def _can_convert_to_int_standalone(value) -> bool:
    try:
        int(value)
        return True
    except (ValueError, TypeError):
        return False


def _can_convert_to_float_standalone(value) -> bool:
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def _can_convert_to_list_standalone(value) -> bool:
    try:
        list(value)
        return True
    except (ValueError, TypeError):
        return False


def _can_convert_to_dict_standalone(value) -> bool:
    if isinstance(value, dict):
        return True
    if isinstance(value, str):
        try:
            json.loads(value)
            return True
        except (ValueError, TypeError):
            return False
    return False


def _is_valid_optional_string_standalone(value: ast.AST) -> bool:
    return isinstance(value, ast.Constant) and (
        value.value is None or isinstance(value.value, str)
    )


def _is_valid_string_standalone(value: ast.AST) -> bool:
    return isinstance(value, ast.Constant) and isinstance(value.value, str)


def _is_valid_class_standalone(value: ast.AST) -> bool:
    return isinstance(value, (ast.Name, ast.Attribute)) or (
        isinstance(value, ast.Constant) and isinstance(value.value, str)
    )


def _is_pathlib_path_call(value: ast.AST) -> bool:
    """Check if the AST node represents a pathlib.Path() constructor call."""
    if not isinstance(value, ast.Call):
        return False

    # All pathlib Path classes
    path_classes = {
        "Path",
        "PosixPath",
        "WindowsPath",
        "PurePath",
        "PurePosixPath",
        "PureWindowsPath",
    }

    # Handle Path() - direct name
    if isinstance(value.func, ast.Name) and value.func.id in path_classes:
        return True

    # Handle pathlib.Path() - attribute access
    return (
        isinstance(value.func, ast.Attribute)
        and value.func.attr in path_classes
        and isinstance(value.func.value, ast.Name)
        and value.func.value.id == "pathlib"
    )


def _is_valid_path_standalone(value: ast.AST) -> bool:
    return (
        isinstance(value, ast.Constant) and isinstance(value.value, str)
    ) or _is_pathlib_path_call(value)


def _is_valid_optional_path_standalone(value: ast.AST) -> bool:
    return (
        isinstance(value, ast.Constant)
        and (value.value is None or isinstance(value.value, str))
    ) or _is_pathlib_path_call(value)


def _is_valid_optional_callable_standalone(value: ast.AST) -> bool:
    if not isinstance(value, ast.Constant):
        return isinstance(value, (ast.Name, ast.Attribute, ast.Lambda))
    if value.value is None:
        return True
    if not isinstance(value.value, str):
        return False
    return looks_like_callable_import_path(value.value)


def _is_valid_optional_int_standalone(value: ast.AST) -> bool:
    return (isinstance(value, ast.Constant) and value.value is None) or (
        isinstance(value, ast.Constant) and _can_convert_to_int_standalone(value.value)
    )


def _is_invalid_bool_value_standalone(value: ast.AST) -> bool:
    if isinstance(value, ast.Constant):
        return value.value not in VALID_BOOL_LITERALS
    return not isinstance(value, ast.Constant)


def _is_invalid_int_value_standalone(value: ast.AST) -> bool:
    if isinstance(value, ast.Constant):
        return not _can_convert_to_int_standalone(value.value)
    return not isinstance(value, (ast.Num, ast.Constant))


def _is_invalid_float_value_standalone(value: ast.AST) -> bool:
    if isinstance(value, ast.Constant):
        return not _can_convert_to_float_standalone(value.value)
    return not isinstance(value, (ast.Num, ast.Constant))


def _is_invalid_list_value_standalone(value: ast.AST) -> bool:
    if isinstance(value, ast.Constant):
        return not _can_convert_to_list_standalone(value.value)
    if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
        return value.func.id not in ("list", "tuple", "set", "range")
    return not isinstance(value, (ast.List, ast.Tuple, ast.Set, ast.Dict))


def _is_invalid_dict_value_standalone(value: ast.AST) -> bool:
    if isinstance(value, ast.Constant):
        return not _can_convert_to_dict_standalone(value.value)
    return not isinstance(value, (ast.Dict, ast.Constant))


def _is_invalid_log_level_value_standalone(value: ast.AST) -> bool:
    if isinstance(value, ast.Constant):
        return (
            not isinstance(value.value, int)
            and value.value not in VALID_LOG_LEVEL_LITERALS
        )
    return type(value) not in {ast.Num, ast.Str, ast.Constant}


def _is_invalid_path_value_standalone(value: ast.AST) -> bool:
    return not _is_valid_path_standalone(value)


def _is_invalid_optional_path_value_standalone(value: ast.AST) -> bool:
    return not _is_valid_optional_path_standalone(value)


def _is_invalid_optional_string_value_standalone(value: ast.AST) -> bool:
    return not _is_valid_optional_string_standalone(value)


def _is_invalid_string_value_standalone(value: ast.AST) -> bool:
    return not _is_valid_string_standalone(value)


def _is_invalid_class_value_standalone(value: ast.AST) -> bool:
    return not _is_valid_class_standalone(value)


def _is_invalid_optional_callable_value_standalone(value: ast.AST) -> bool:
    return not _is_valid_optional_callable_standalone(value)


def _is_invalid_optional_int_value_standalone(value: ast.AST) -> bool:
    return not _is_valid_optional_int_standalone(value)


def _is_invalid_dict_or_list_value_standalone(value: ast.AST) -> bool:
    return not _is_valid_dict_or_list_standalone(value)


def _is_invalid_user_agent_standalone(value: ast.AST) -> bool:
    """Check if USER_AGENT value lacks contact information (SCP22)."""
    if not isinstance(value, ast.Constant):
        return isinstance(value, (ast.Num, ast.List, ast.Dict, ast.Set, ast.Tuple))

    if not isinstance(value.value, str):
        return True

    user_agent = value.value
    if not user_agent:
        return True

    # Check for placeholder text that should be replaced
    if (
        "(+http://www.yourdomain.com)" in user_agent
        or "(+https://scrapy.org)" in user_agent
    ):
        return True

    # Check for browser user agent patterns (these lack contact info)
    browser_patterns = [
        r"Mozilla/\d+\.\d+",
        r"Chrome/\d+\.\d+",
        r"Safari/\d+\.\d+",
        r"Firefox/\d+\.\d+",
        r"AppleWebKit/\d+\.\d+",
        r"Gecko/\d+",
    ]
    for pattern in browser_patterns:
        if re.search(pattern, user_agent):
            return True

    # Check for contact information patterns
    url_pattern = (
        r"https?://[a-zA-Z0-9.-]+|www\.[a-zA-Z0-9.-]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    )
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    phone_pattern = r"\b\d{3}[-.]\d{4}\b|\b\d{10,}\b|\b\(\d{3}\)\s?\d{3}[-.]\d{4}\b"

    return not (
        re.search(url_pattern, user_agent)
        or re.search(email_pattern, user_agent)
        or re.search(phone_pattern, user_agent)
    )


def _is_valid_dict_or_list_standalone(value: ast.AST) -> bool:
    # Allow None, strings, tuples, dicts, or lists
    if isinstance(value, ast.Constant) and value.value is None:
        return True
    if isinstance(value, ast.Constant):
        return isinstance(value.value, (str, tuple, dict, list))
    return isinstance(value, (ast.Tuple, ast.Dict, ast.List))


def _is_invalid_enum_str_value_standalone(setting: str, value: ast.AST) -> bool:
    if setting not in SETTINGS:
        return False
    setting_info = SETTINGS[setting]
    if not setting_info.allowed_values:
        return False

    if isinstance(value, ast.Constant):
        if value.value is None:
            return True  # None is not allowed for ENUM_STR
        if not isinstance(value.value, str):
            return True  # Must be a string
        return value.value not in setting_info.allowed_values

    # If it's not a constant, it's invalid for ENUM_STR
    return True


def _is_invalid_periodic_log_config_value_standalone(value: ast.AST) -> bool:
    return not validate_periodic_log_config_ast(value)


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
VALID_BOOL_TYPES: set[type] = {str, int, bool}

# Known valid literal values for log level settings
# (additional, arbitrary int values are also supported)
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

# Valid types for log level settings when literal value cannot be determined
VALID_LOG_LEVEL_TYPES: set[type] = {str, int}

# Valid literal values for int settings that are unbounded
# (i.e., no max value validation required)
VALID_INT_LITERALS = (int,)

# Valid literal values for float settings
VALID_FLOAT_LITERALS = (float, int)

# Default settings that are allowed to be None
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

TYPE_TO_METHOD: dict[SettingType, str] = {
    SettingType.BOOL: "getbool",
    SettingType.INT: "getint",
    SettingType.FLOAT: "getfloat",
    SettingType.LIST: "getlist",
    SettingType.DICT: "getdict",
    SettingType.DICT_OR_LIST: "getdictorlist",
    SettingType.BASED_DICT: "getwithbase",
}


class SettingsIssueFinder(ast.NodeVisitor):
    def __init__(
        self, config, filename=None, allowed_settings=None, exclude_settings=None
    ):
        super().__init__()
        self.config = config
        self.filename = filename
        self.issues = []
        self.found_settings = set()

        # Initialize allowed and exclude settings
        self.allowed_settings = set(allowed_settings) if allowed_settings else set()
        self.exclude_settings = set(exclude_settings) if exclude_settings else set()

        # Initialize known settings
        self.known_settings = set(SETTINGS)
        if allowed_settings:
            self.known_settings.update(allowed_settings)

        # Initialize setting type mappings
        self.deprecated_settings = self._get_deprecated_settings()
        self.future_settings = self._get_future_settings()
        self.removed_settings = self._get_removed_settings()
        self.missing_package_settings = self._get_missing_package_settings()
        self.typed_settings = {
            name: info.type for name, info in SETTINGS.items() if info.type is not None
        }

        # Settings methods for checking
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

    def _get_deprecated_settings(self) -> set[str]:
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

    def _get_future_settings(self) -> set[str]:
        future = set()
        for name, info in SETTINGS.items():
            if not info.added_version:
                continue
            package_version = self.get_package_version(info.package)
            if package_version is not None and is_version_greater_than(
                info.added_version, package_version
            ):
                future.add(name)
        return future

    def _get_removed_settings(self) -> set[str]:
        removed = set()
        for name, info in SETTINGS.items():
            if not info.removed_version:
                continue
            package_version = self.get_package_version(info.package)
            if package_version is not None and is_version_less_than_or_equal(
                info.removed_version, package_version
            ):
                removed.add(name)
        return removed

    def _get_missing_package_settings(self) -> set[str]:
        missing = set()
        for name, info in SETTINGS.items():
            if (
                info.package != "scrapy"
                and self.get_package_version(info.package) is None
            ):
                missing.add(name)
        return missing

    def get_package_version(self, package_name) -> Version | None:
        return self.package_versions.get(canonicalize_name(package_name), None)

    @property
    def package_versions(self) -> dict[str, Version]:
        if hasattr(self, "_package_versions"):
            return self._package_versions
        self._package_versions = build_package_versions_dict(self.get_project_root())
        return self._package_versions

    def get_project_root(self):
        if not self.filename:
            return None
        path = Path(self.filename).resolve()
        for parent in [path, *list(path.parents)]:
            if (parent / "scrapy.cfg").exists():
                return parent
        return None

    def visit_Assign(self, node: ast.Assign) -> None:
        self._check_assignment(node)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        self._check_call(node)
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        self._check_subscript(node)
        self.generic_visit(node)

    def visit_Delete(self, node: ast.Delete) -> None:
        self._check_delete(node)
        self.generic_visit(node)

    def _check_assignment(self, node: ast.Assign) -> None:
        for target in node.targets:
            # Check custom_settings assignments
            if isinstance(target, ast.Name) and target.id == "custom_settings":
                if isinstance(node.value, ast.Dict):
                    self._check_dict_keys(
                        node.value,
                        node.lineno,
                        node.col_offset,
                        node.value,
                        "assignment",
                    )
                elif (
                    isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name)
                    and node.value.func.id == "dict"
                ):
                    self._check_dict_constructor_keywords(node.value, "assignment")

            # Handle subscript assignment: settings["SETTING"] = "value"
            elif (
                isinstance(target, ast.Subscript)
                and self._is_settings_subscript(target)
                and isinstance(target.slice, ast.Constant)
                and isinstance(target.slice.value, str)
            ):
                setting_name = target.slice.value
                self._check_setting_issues(
                    setting_name,
                    target.slice.lineno,
                    target.slice.col_offset,
                    node.value,
                    "assignment",
                )

    def _check_call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Attribute):
            if self._is_settings_method_call(node):
                self._check_settings_method_args(node)
                return
            if self._is_settings_dict_method_call(node):
                self._check_settings_dict_method_args(node)
                return
            if self._is_settings_constructor_call(node):
                self._check_settings_constructor_args(node)
                return
            if node.func.attr == "overridden_settings":
                if (
                    isinstance(node.func.value, ast.Attribute)
                    and node.func.value.attr == "settings"
                    and isinstance(node.func.value.value, ast.Name)
                    and node.func.value.value.id == "scrapy"
                ):
                    self._check_overridden_settings_args(node)
                    return
                if (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "settings"
                ):
                    self._check_overridden_settings_args(node)
                return

        if self._is_settings_constructor_call(node):
            self._check_settings_constructor_args(node)
            return
        if isinstance(node.func, ast.Name) and node.func.id == "overridden_settings":
            self._check_overridden_settings_args(node)

    def _check_subscript(self, node: ast.Subscript) -> None:
        if not self._is_settings_subscript(node):
            return
        if not isinstance(node.slice, ast.Constant) or not isinstance(
            node.slice.value, str
        ):
            return
        setting_name = node.slice.value

        # Check for type mismatch (SCP17) only for read operations (Load context), not write operations (Store context)
        if isinstance(node.ctx, ast.Load) and self._should_report_type_mismatch(
            setting_name, "get"
        ):  # Treat subscript like get()
            issue_key_base = (
                f"{setting_name}:{node.slice.lineno}:{node.slice.col_offset}"
            )
            issue_key = f"SCP17:{issue_key_base}"
            if issue_key not in self.found_settings:
                self.found_settings.add(issue_key)
                message = "wrong setting getter"
                self.issues.append(
                    Issue(
                        17,
                        message,
                        line=node.slice.lineno,
                        column=node.slice.col_offset,
                    )
                )

        self._check_setting_issues(
            setting_name, node.slice.lineno, node.slice.col_offset, None, "subscript"
        )

    def _check_delete(self, node: ast.Delete) -> None:
        for target in node.targets:
            if not isinstance(target, ast.Subscript):
                continue
            if not self._is_settings_object(target.value):
                continue
            if not isinstance(target.slice, ast.Constant) or not isinstance(
                target.slice.value, str
            ):
                continue
            setting_name = target.slice.value
            self._check_setting_issues(
                setting_name,
                target.slice.lineno,
                target.slice.col_offset,
                None,
                "delete",
            )

    def _check_setting_issues(  # noqa: PLR0912, PLR0915
        self,
        setting_name: str,
        line: int,
        col: int,
        value: ast.AST | None = None,
        context: str = "general",
    ) -> None:
        # Track each issue type separately to avoid duplicates
        issue_key_base = f"{setting_name}:{line}:{col}"

        # Check for missing package settings first (SCP15)
        if self._should_report_missing_package_setting(setting_name):
            issue_key = f"SCP15:{issue_key_base}"
            if issue_key not in self.found_settings:
                self.found_settings.add(issue_key)
                message = "missing setting requirement"
                self.issues.append(Issue(15, message, line=line, column=col))
                return

        # Check for deprecated settings (SCP08)
        if self._should_report_deprecated_setting(setting_name):
            issue_key = f"SCP08:{issue_key_base}"
            if issue_key not in self.found_settings:
                self.found_settings.add(issue_key)
                message = "deprecated setting"
                self.issues.append(Issue(8, message, line=line, column=col))

        # Check for future settings (SCP09)
        if self._should_report_future_setting(setting_name):
            issue_key = f"SCP09:{issue_key_base}"
            if issue_key not in self.found_settings:
                self.found_settings.add(issue_key)
                self.issues.append(
                    Issue(9, "setting requires upgrade", line=line, column=col)
                )

        # Check for removed settings (SCP10)
        if self._should_report_removed_setting(setting_name):
            issue_key = f"SCP10:{issue_key_base}"
            if issue_key not in self.found_settings:
                self.found_settings.add(issue_key)
                message = "removed setting"
                self.issues.append(Issue(10, message, line=line, column=col))

        # Check for unknown settings (SCP07)
        if self._should_report_unknown_setting(setting_name):
            issue_key = f"SCP07:{issue_key_base}"
            if issue_key not in self.found_settings:
                self.found_settings.add(issue_key)
                suggestions = get_setting_suggestions(setting_name, self.known_settings)
                message = "unknown setting"
                detail = None
                if suggestions:
                    if len(suggestions) == 1:
                        detail = f"did you mean {suggestions[0]}?"
                    else:
                        suggestion_list = ", ".join(suggestions)
                        detail = f"did you mean one of: {suggestion_list}?"
                self.issues.append(
                    Issue(7, message, detail=detail, line=line, column=col)
                )

        # Check for base setting name issues (SCP24)
        if self._should_report_base_setting_name(setting_name):
            issue_key = f"SCP24:{issue_key_base}"
            if issue_key not in self.found_settings:
                self.found_settings.add(issue_key)
                message = "use of BASE setting"
                self.issues.append(Issue(24, message, line=line, column=col))

        # Only check these for assignments and set() method calls, not other method calls
        if context in ("assignment", "method_call_set") and value:
            value_issues = get_setting_value_issues(setting_name, value, self.config)
            for issue in value_issues:
                issue_key = f"SCP{issue.code:02}:{issue_key_base}"
                if issue_key not in self.found_settings:
                    self.found_settings.add(issue_key)
                    # Use the issue's column if available, otherwise fall back to provided column
                    issue_col = issue.column if issue.column != 0 else col
                    self.issues.append(
                        Issue(issue.code, issue.summary, line=line, column=issue_col)
                    )

    def _should_report_missing_package_setting(self, setting_name: str) -> bool:
        return (
            setting_name in self.missing_package_settings
            and setting_name not in self.allowed_settings
        )

    def _should_report_deprecated_setting(self, setting_name: str) -> bool:
        return (
            setting_name in self.deprecated_settings
            and setting_name not in self.allowed_settings
            and setting_name not in self.exclude_settings
        )

    def _should_report_future_setting(self, setting_name: str) -> bool:
        return (
            setting_name in self.future_settings
            and setting_name not in self.allowed_settings
            and setting_name not in self.exclude_settings
        )

    def _should_report_removed_setting(self, setting_name: str) -> bool:
        return (
            setting_name in self.removed_settings
            and setting_name not in self.allowed_settings
            and setting_name not in self.exclude_settings
        )

    def _should_report_unknown_setting(self, setting_name: str) -> bool:
        return (
            setting_name not in self.known_settings
            and setting_name not in self.exclude_settings
        )

    def _should_report_base_setting_name(self, setting_name: str) -> bool:
        return setting_name.endswith("_BASE") and setting_name in SETTINGS

    def _should_report_invalid_value(self, setting_name: str, value: ast.AST) -> bool:
        if setting_name not in SETTINGS:
            return False
        if (
            setting_name in self.allowed_settings
            or setting_name in self.exclude_settings
        ):
            return False
        return self._is_invalid_value(setting_name, value)

    def _should_report_import_path_string(
        self, setting_name: str, value: ast.AST
    ) -> bool:
        return (
            setting_name in SETTINGS
            and SETTINGS[setting_name].type == SettingType.CLS
            and self._is_import_path_string_value(value)
        )

    def _is_invalid_value(self, setting_name: str, value: ast.AST) -> bool:  # noqa: PLR0911, PLR0912
        setting_info = SETTINGS[setting_name]
        setting_type = setting_info.type

        if setting_type == SettingType.BOOL:
            return self._is_invalid_bool_value(value)
        if setting_type == SettingType.INT:
            return self._is_invalid_int_value(value)
        if setting_type == SettingType.FLOAT:
            return self._is_invalid_float_value(value)
        if setting_type == SettingType.LIST:
            return self._is_invalid_list_value(value)
        if setting_type == SettingType.DICT:
            return self._is_invalid_dict_value(value)
        if setting_type == SettingType.LOG_LEVEL:
            return self._is_invalid_log_level_value(value)
        if setting_type == SettingType.PATH:
            return self._is_invalid_path_value(value)
        if setting_type == SettingType.OPT_PATH:
            return self._is_invalid_optional_path_value(value)
        if setting_type == SettingType.OPT_STR:
            return self._is_invalid_optional_string_value(value)
        if setting_type == SettingType.STR:
            return self._is_invalid_string_value(value)
        if setting_type == SettingType.CLS:
            return self._is_invalid_class_value(value)
        if setting_type == SettingType.OPT_CALLABLE:
            return self._is_invalid_optional_callable_value(value)
        if setting_type == SettingType.OPT_INT:
            return self._is_invalid_optional_int_value(value)

        return False

    def _is_invalid_bool_value(self, value: ast.AST) -> bool:
        if isinstance(value, ast.Constant):
            return value.value not in VALID_BOOL_LITERALS
        return not isinstance(value, ast.Constant)

    def _is_invalid_int_value(self, value: ast.AST) -> bool:
        if isinstance(value, ast.Constant):
            return not self._can_convert_to_int(value.value)
        return not isinstance(value, (ast.Num, ast.Constant))

    def _is_invalid_float_value(self, value: ast.AST) -> bool:
        if isinstance(value, ast.Constant):
            return not self._can_convert_to_float(value.value)
        return not isinstance(value, (ast.Num, ast.Constant))

    def _is_invalid_list_value(self, value: ast.AST) -> bool:
        if isinstance(value, ast.Constant):
            return not self._can_convert_to_list(value.value)
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
            return value.func.id not in ("list", "tuple", "set")
        return not isinstance(value, (ast.List, ast.Tuple, ast.Set, ast.Constant))

    def _is_invalid_dict_value(self, value: ast.AST) -> bool:
        if isinstance(value, ast.Constant):
            return not self._can_convert_to_dict(value.value)
        return not isinstance(value, (ast.Dict, ast.Constant))

    def _is_invalid_log_level_value(self, value: ast.AST) -> bool:
        if isinstance(value, ast.Constant):
            return (
                not isinstance(value.value, int)
                and value.value not in VALID_LOG_LEVEL_LITERALS
            )
        return type(value) not in {ast.Num, ast.Str, ast.Constant}

    def _is_invalid_path_value(self, value: ast.AST) -> bool:
        return not self._is_valid_path(value)

    def _is_invalid_optional_path_value(self, value: ast.AST) -> bool:
        return not self._is_valid_optional_path(value)

    def _is_invalid_optional_string_value(self, value: ast.AST) -> bool:
        return not self._is_valid_optional_string(value)

    def _is_invalid_string_value(self, value: ast.AST) -> bool:
        return not self._is_valid_string(value)

    def _is_invalid_class_value(self, value: ast.AST) -> bool:
        return not self._is_valid_class(value)

    def _is_invalid_optional_callable_value(self, value: ast.AST) -> bool:
        return not self._is_valid_optional_callable(value)

    def _is_invalid_optional_int_value(self, value: ast.AST) -> bool:
        return not self._is_valid_optional_int(value)

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
        if isinstance(value, dict):
            return True
        if isinstance(value, str):
            try:
                json.loads(value)
                return True
            except (ValueError, TypeError):
                return False
        return False

    def _is_valid_optional_string(self, value: ast.AST) -> bool:
        return value is None or isinstance(value, ast.Constant)

    def _is_valid_string(self, value: ast.AST) -> bool:
        return isinstance(value, ast.Constant)

    def _is_valid_class(self, value: ast.AST) -> bool:
        if not isinstance(value, ast.Constant):
            return True
        if not isinstance(value.value, str):
            return False
        return looks_like_class_import_path(value.value)

    def _is_valid_path(self, value: ast.AST) -> bool:
        return (
            isinstance(value, ast.Constant) and isinstance(value.value, str)
        ) or _is_pathlib_path_call(value)

    def _is_valid_optional_path(self, value: ast.AST) -> bool:
        return (
            isinstance(value, ast.Constant)
            and (value.value is None or isinstance(value.value, str))
        ) or _is_pathlib_path_call(value)

    def _is_valid_optional_callable(self, value: ast.AST) -> bool:
        if not isinstance(value, ast.Constant):
            return True
        if value.value is None:
            return True
        if not isinstance(value.value, str):
            return False
        return looks_like_callable_import_path(value.value)

    def _is_valid_optional_int(self, value: ast.AST) -> bool:
        if not isinstance(value, ast.Constant):
            return True
        return value.value is None or self._can_convert_to_int(value.value)

    def _is_import_path_string_value(self, value: ast.AST) -> bool:
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            return looks_like_class_import_path(value.value)
        return False

    def _is_settings_method_call(self, node: ast.Call) -> bool:
        assert isinstance(node.func, ast.Attribute)
        method_name = node.func.attr
        if method_name not in self.settings_methods:
            return False
        return self._is_settings_object(node.func.value)

    def _is_settings_dict_method_call(self, node: ast.Call) -> bool:
        assert isinstance(node.func, ast.Attribute)
        method_name = node.func.attr
        dict_methods = {"setdict", "update"}
        if method_name not in dict_methods:
            return False
        return self._is_settings_object(node.func.value)

    def _is_settings_subscript(self, node: ast.Subscript) -> bool:
        return self._is_settings_object(node.value)

    def _is_settings_object(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Name):
            return node.id == "settings"
        if not isinstance(node, ast.Attribute):
            return False
        return node.attr == "settings"

    def _is_settings_constructor_call(self, node: ast.Call) -> bool:
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

    def _check_settings_method_args(self, node: ast.Call) -> None:  # noqa: PLR0912, PLR0915
        assert isinstance(node.func, ast.Attribute)
        method_name = node.func.attr
        param_name = self.settings_methods[method_name]

        if node.args:
            first_arg = node.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                setting_name = first_arg.value

                # Method-specific checks that only apply to getter methods
                issue_key_base = (
                    f"{setting_name}:{first_arg.lineno}:{first_arg.col_offset}"
                )

                # Check for type mismatch (SCP17)
                if self._should_report_type_mismatch(setting_name, method_name):
                    issue_key = f"SCP17:{issue_key_base}"
                    if issue_key not in self.found_settings:
                        self.found_settings.add(issue_key)
                        message = "wrong setting getter"
                        self.issues.append(
                            Issue(
                                17,
                                message,
                                line=first_arg.lineno,
                                column=first_arg.col_offset,
                            )
                        )

                # Check for unnecessary get (SCP25)
                if self._should_report_unnecessary_get(setting_name, method_name, node):
                    issue_key = f"SCP25:{issue_key_base}"
                    if issue_key not in self.found_settings:
                        self.found_settings.add(issue_key)
                        message = "unneeded setting get"
                        self.issues.append(
                            Issue(
                                25,
                                message,
                                line=first_arg.lineno,
                                column=first_arg.col_offset,
                            )
                        )

                # Check for ignored get default (SCP26)
                if self._should_report_ignored_get_default(
                    setting_name, method_name, node
                ):
                    issue_key = f"SCP26:{issue_key_base}"
                    if issue_key not in self.found_settings:
                        self.found_settings.add(issue_key)
                        message = "ignored getter default"
                        # Point to the default value (second argument) instead of setting name
                        default_arg = node.args[1]
                        self.issues.append(
                            Issue(
                                26,
                                message,
                                line=default_arg.lineno,
                                column=default_arg.col_offset,
                            )
                        )

                # Check general setting issues (but not method-specific ones)
                MIN_ARGS_FOR_VALUE = 2
                if len(node.args) >= MIN_ARGS_FOR_VALUE:
                    value = node.args[1]
                    # Use special context for set() and setdefault() methods to enable SCP18 checking
                    context = (
                        "method_call_set"
                        if method_name in ("set", "setdefault")
                        else "method_call"
                    )
                    self._check_setting_issues(
                        setting_name,
                        first_arg.lineno,
                        first_arg.col_offset,
                        value,
                        context,
                    )
                else:
                    self._check_setting_issues(
                        setting_name,
                        first_arg.lineno,
                        first_arg.col_offset,
                        None,
                        "method_call",
                    )

        for keyword in node.keywords:
            if keyword.arg != param_name:
                continue
            if not isinstance(keyword.value, ast.Constant) or not isinstance(
                keyword.value.value, str
            ):
                continue
            setting_name = keyword.value.value

            # Method-specific checks that only apply to getter methods (for keyword args)
            issue_key_base = (
                f"{setting_name}:{keyword.value.lineno}:{keyword.value.col_offset}"
            )

            # Check for type mismatch (SCP17)
            if self._should_report_type_mismatch(setting_name, method_name):
                issue_key = f"SCP17:{issue_key_base}"
                if issue_key not in self.found_settings:
                    self.found_settings.add(issue_key)
                    message = "wrong setting getter"
                    self.issues.append(
                        Issue(
                            17,
                            message,
                            line=keyword.value.lineno,
                            column=keyword.value.col_offset,
                        )
                    )

            # Check for unnecessary get (SCP25)
            if self._should_report_unnecessary_get(setting_name, method_name, node):
                issue_key = f"SCP25:{issue_key_base}"
                if issue_key not in self.found_settings:
                    self.found_settings.add(issue_key)
                    message = "unneeded setting get"
                    self.issues.append(
                        Issue(
                            25,
                            message,
                            line=keyword.value.lineno,
                            column=keyword.value.col_offset,
                        )
                    )

            # Check for ignored get default (SCP26)
            if self._should_report_ignored_get_default(setting_name, method_name, node):
                issue_key = f"SCP26:{issue_key_base}"
                if issue_key not in self.found_settings:
                    self.found_settings.add(issue_key)
                    message = "ignored getter default"
                    # Point to the default value (second argument) instead of setting name
                    default_arg = node.args[1]
                    self.issues.append(
                        Issue(
                            26,
                            message,
                            line=default_arg.lineno,
                            column=default_arg.col_offset,
                        )
                    )

            # Check general setting issues (but not method-specific ones)
            self._check_setting_issues(
                setting_name,
                keyword.value.lineno,
                keyword.value.col_offset,
                None,
                "method_call",
            )

    def _should_report_type_mismatch(self, setting_name: str, method_name: str) -> bool:
        if setting_name not in self.typed_settings:
            return False
        if (
            setting_name in self.allowed_settings
            or setting_name in self.exclude_settings
        ):
            return False

        setting_type = self.typed_settings[setting_name]

        # If the setting has a specific typed getter
        if setting_type in TYPE_TO_METHOD:
            expected_method = TYPE_TO_METHOD[setting_type]
            # Wrong if using get() instead of typed getter, or using wrong typed getter
            return method_name != expected_method and (
                method_name == "get"
                or method_name
                in {
                    "getbool",
                    "getint",
                    "getfloat",
                    "getlist",
                    "getdict",
                    "getdictorlist",
                    "getwithbase",
                }
            )
        # Setting should use get() or subscript, but someone used a typed getter
        return method_name in {
            "getbool",
            "getint",
            "getfloat",
            "getlist",
            "getdict",
            "getdictorlist",
            "getwithbase",
        }

    def _should_report_unnecessary_get(
        self, setting_name: str, method_name: str, node: ast.Call
    ) -> bool:
        if setting_name not in SETTINGS:
            return False
        if method_name != "get":
            return False
        setting_info = SETTINGS[setting_name]
        if setting_info.type is not None and setting_info.type in TYPE_TO_METHOD:
            return False
        # Don't report SCP25 if a meaningful (non-None) default is provided
        MIN_ARGS_FOR_DEFAULT = 2
        if len(node.args) >= MIN_ARGS_FOR_DEFAULT:
            default_arg = node.args[1]
            if isinstance(default_arg, ast.Constant) and default_arg.value is not None:
                return False
        return True

    def _should_report_ignored_get_default(
        self, setting_name: str, method_name: str, node: ast.Call
    ) -> bool:
        if setting_name not in SETTINGS:
            return False

        # Check if this is a getter method that supports defaults
        getter_methods = {"get", "getbool", "getint", "getfloat", "getlist", "getdict"}
        MIN_ARGS_FOR_DEFAULT = 2
        if method_name not in getter_methods or len(node.args) < MIN_ARGS_FOR_DEFAULT:
            return False

        # If explicit default is None, always report since get() returns None by default anyway
        if isinstance(node.args[1], ast.Constant) and node.args[1].value is None:
            return True

        # For other defaults, only report if setting is in DEFAULT_SETTINGS and has conflicting default
        if setting_name not in DEFAULT_SETTINGS:
            return False

        # For settings with None default, providing non-None default is fine
        # For settings with non-None defaults, providing any default is redundant
        return setting_name not in DEFAULT_SETTINGS_WITH_NONE

    def _check_dict_keys(
        self,
        dict_node: ast.Dict,
        line: int,
        col: int,
        value_context: ast.AST | None = None,
        context: str = "dict",
    ) -> None:
        for key, value in zip(dict_node.keys, dict_node.values):
            if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                continue
            setting_name = key.value
            if setting_name.isupper():
                self._check_setting_issues(
                    setting_name, key.lineno, key.col_offset, value, context
                )

    def _check_dict_constructor_keywords(
        self, call_node: ast.Call, context: str = "dict"
    ) -> None:
        for keyword in call_node.keywords:
            if keyword.arg is None:
                continue
            setting_name = keyword.arg
            if setting_name.isupper():
                keyword_col = keyword.value.col_offset - len(setting_name) - 1
                self._check_setting_issues(
                    setting_name,
                    keyword.value.lineno,
                    keyword_col,
                    keyword.value,
                    context,
                )

    def _check_settings_dict_method_args(self, node: ast.Call) -> None:
        method_name = node.func.attr
        # Use special context for setdict() and update() methods to enable SCP18 checking
        context = "method_call_set" if method_name in ("setdict", "update") else "dict"

        if node.args:
            first_arg = node.args[0]
            if isinstance(first_arg, ast.Dict):
                self._check_dict_keys(
                    first_arg, first_arg.lineno, first_arg.col_offset, context=context
                )
            elif (
                isinstance(first_arg, ast.Call)
                and isinstance(first_arg.func, ast.Name)
                and first_arg.func.id == "dict"
            ):
                self._check_dict_constructor_keywords(first_arg, context=context)
        for keyword in node.keywords:
            if keyword.arg != "values":
                continue
            if isinstance(keyword.value, ast.Dict):
                self._check_dict_keys(
                    keyword.value,
                    keyword.value.lineno,
                    keyword.value.col_offset,
                    context=context,
                )
            elif (
                isinstance(keyword.value, ast.Call)
                and isinstance(keyword.value.func, ast.Name)
                and keyword.value.func.id == "dict"
            ):
                self._check_dict_constructor_keywords(keyword.value, context=context)

    def _check_settings_constructor_args(self, node: ast.Call) -> None:
        for arg in node.args:
            if isinstance(arg, ast.Dict):
                self._check_dict_keys(arg, arg.lineno, arg.col_offset)
            elif (
                isinstance(arg, ast.Call)
                and isinstance(arg.func, ast.Name)
                and arg.func.id == "dict"
            ):
                self._check_dict_constructor_keywords(arg)
        for keyword in node.keywords:
            if keyword.arg != "values":
                continue
            if isinstance(keyword.value, ast.Dict):
                self._check_dict_keys(
                    keyword.value, keyword.value.lineno, keyword.value.col_offset
                )
            elif (
                isinstance(keyword.value, ast.Call)
                and isinstance(keyword.value.func, ast.Name)
                and keyword.value.func.id == "dict"
            ):
                self._check_dict_constructor_keywords(keyword.value)

    def _check_overridden_settings_args(self, node: ast.Call) -> None:
        if node.args:
            first_arg = node.args[0]
            if isinstance(first_arg, ast.Dict):
                self._check_dict_keys(first_arg, first_arg.lineno, first_arg.col_offset)
            elif (
                isinstance(first_arg, ast.Call)
                and isinstance(first_arg.func, ast.Name)
                and first_arg.func.id == "dict"
            ):
                self._check_dict_constructor_keywords(first_arg)
        for keyword in node.keywords:
            if keyword.arg != "settings":
                continue
            if isinstance(keyword.value, ast.Dict):
                self._check_dict_keys(
                    keyword.value, keyword.value.lineno, keyword.value.col_offset
                )
            elif (
                isinstance(keyword.value, ast.Call)
                and isinstance(keyword.value.func, ast.Name)
                and keyword.value.func.id == "dict"
            ):
                self._check_dict_constructor_keywords(keyword.value)
