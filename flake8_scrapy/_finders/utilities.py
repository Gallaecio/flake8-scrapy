from __future__ import annotations

import ast
import json
from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version


def is_valid_log_level(value) -> bool:
    """Check if a value is a valid logging level."""
    # Accept any integer (logging accepts any integer level)
    if isinstance(value, int):
        return True

    # Accept valid string logging level names (case-insensitive)
    if isinstance(value, str):
        return value.upper() in {
            "CRITICAL",
            "FATAL",
            "ERROR",
            "WARNING",
            "WARN",
            "INFO",
            "DEBUG",
            "NOTSET",
        }

    # Reject None and other types
    return False


def looks_like_class_import_path(value: str) -> bool:
    """Check if a string looks like a valid import path for a class."""
    if not value:
        return False
    parts = value.split(".")
    MINIMUM_IMPORT_PARTS = 2
    if len(parts) < MINIMUM_IMPORT_PARTS:
        return False
    for part in parts:
        if not part.isidentifier():
            return False
    return parts[-1][0].isupper()


def looks_like_callable_import_path(value: str) -> bool:
    """Check if a string looks like a valid import path for any callable (function, class, etc.)."""
    if not value:
        return False
    parts = value.split(".")
    MINIMUM_IMPORT_PARTS = 2
    if len(parts) < MINIMUM_IMPORT_PARTS:
        return False
    return all(part.isidentifier() for part in parts)


def parse_requirement_line(line: str) -> Requirement | None:
    """Parse a requirement line and return a Requirement object if valid."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if line.startswith("-"):
        return None
    if "#" in line:
        line = line.split("#")[0].strip()
    try:
        return Requirement(line)
    except InvalidRequirement:
        # This handles URLs, local paths, and other non-standard formats
        return None


def is_frozen_requirement(req: Requirement) -> bool:
    """Check if a requirement is frozen (has an exact version pin)."""
    return len(req.specifier) == 1 and next(iter(req.specifier)).operator == "=="


def is_version_less_than(version: str | Version, min_version: str | Version) -> bool:
    """Compare two versions, returning True if version < min_version."""
    try:
        v1 = version if isinstance(version, Version) else Version(version)
        v2 = min_version if isinstance(min_version, Version) else Version(min_version)
        return v1 < v2
    except InvalidVersion:
        return False


def is_version_greater_than(version: str | Version, min_version: str | Version) -> bool:
    """Compare two versions, returning True if version > min_version."""
    try:
        v1 = version if isinstance(version, Version) else Version(version)
        v2 = min_version if isinstance(min_version, Version) else Version(min_version)
        return v1 > v2
    except InvalidVersion:
        return False


def is_version_less_than_or_equal(
    version: str | Version, max_version: str | Version
) -> bool:
    """Compare two versions, returning True if version <= max_version."""
    try:
        v1 = version if isinstance(version, Version) else Version(version)
        v2 = max_version if isinstance(max_version, Version) else Version(max_version)
        return v1 <= v2
    except InvalidVersion:
        return False


def get_package_version_from_requirements(
    package_name: str, project_root: Path | None
) -> Version | None:
    """Get the version of a package from requirements.txt."""
    if not project_root:
        return None

    requirements_txt = project_root / "requirements.txt"
    if not requirements_txt.exists():
        return None

    try:
        requirements = requirements_txt.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    for line in requirements.splitlines():
        requirement = parse_requirement_line(line)
        if requirement is None:
            continue
        if not is_frozen_requirement(requirement):
            continue
        if canonicalize_name(requirement.name) == canonicalize_name(package_name):
            version = next(iter(requirement.specifier)).version
            return Version(version)

    return None


def build_package_versions_dict(project_root: Path | None) -> dict[str, Version]:
    """Build a dictionary of package names to versions from requirements.txt."""
    package_versions = {}
    if not project_root:
        return package_versions

    requirements_txt = project_root / "requirements.txt"
    if not requirements_txt.exists():
        return package_versions

    try:
        requirements = requirements_txt.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return package_versions

    for line in requirements.splitlines():
        requirement = parse_requirement_line(line)
        if requirement is None:
            continue
        if not is_frozen_requirement(requirement):
            continue
        version = next(iter(requirement.specifier)).version
        package_versions[canonicalize_name(requirement.name)] = Version(version)

    return package_versions


def format_issue_message(msg_code: str, msg_info: str, detail: str = "") -> str:
    """Format a standard issue message with optional detail."""
    base_message = f"{msg_code} {msg_info}"
    if detail:
        return f"{base_message}: {detail}"
    return base_message


def format_version_issue_message(
    msg_code: str, msg_info: str, actual_version: str, minimum_version: str
) -> str:
    """Format a version-related issue message."""
    detail = f"{actual_version} (minimum required: {minimum_version})"
    return format_issue_message(msg_code, msg_info, detail)


def format_replacement_message(
    msg_code: str, msg_info: str, package_name: str, replacements: list[str]
) -> str:
    """Format a package replacement message."""
    if len(replacements) == 1:
        replacement_text = replacements[0]
    else:
        replacement_text = " or ".join(replacements)
    detail = f"{package_name} (use {replacement_text} instead)"
    return format_issue_message(msg_code, msg_info, detail)


def check_package_obsolescence(
    package_name: str, obsolete_packages: dict[str, list[str]]
) -> tuple[bool, list[str]]:
    """Check if a package is obsolete and return replacement suggestions."""
    package_lower = package_name.lower()
    if package_lower in obsolete_packages:
        return True, obsolete_packages[package_lower]
    return False, []


def extract_version_from_requirement(req: Requirement) -> str | None:
    """Extract version string from a frozen requirement."""
    if not is_frozen_requirement(req):
        return None
    return next(iter(req.specifier)).version


def validate_feeds_config(  # noqa: PLR0911
    value_node: ast.AST, feeds_key_versions: dict[str, str], get_package_version_func
) -> str:
    """Get specific validation error for FEEDS setting, or empty string if valid."""
    # FEEDS must be a dict
    if isinstance(value_node, ast.Constant):
        value = value_node.value
        if isinstance(value, dict):
            return _validate_feeds_dict(
                value, feeds_key_versions, get_package_version_func
            )
        if isinstance(value, str):
            try:
                parsed_value = json.loads(value)
                if not isinstance(parsed_value, dict):
                    return "must be a dict"
                return _validate_feeds_dict(
                    parsed_value, feeds_key_versions, get_package_version_func
                )
            except (json.JSONDecodeError, TypeError):
                return "must be a dict"
        else:
            return "must be a dict"

    if isinstance(value_node, ast.Dict):
        return _validate_feeds_dict_ast(
            value_node, feeds_key_versions, get_package_version_func
        )

    # Any other AST node type is invalid for FEEDS
    return "must be a dict"


def _validate_feeds_dict(
    feeds_dict: dict, feeds_key_versions: dict[str, str], get_package_version_func
) -> str:
    """Get validation error for a FEEDS dict value at runtime."""
    for key, feed_config in feeds_dict.items():
        # Root keys may be strings or Path objects
        if not isinstance(key, (str, Path)):
            return f"key {key!r} must be a string or Path object"

        # Feed config must be a dict
        if not isinstance(feed_config, dict):
            return f"feed config for {key!r} must be a dict"

        # Validate feed config keys and values
        error = _validate_feed_config(
            key, feed_config, feeds_key_versions, get_package_version_func
        )
        if error:
            return error

    return ""


def _validate_feeds_dict_ast(
    dict_node: ast.Dict, feeds_key_versions: dict[str, str], get_package_version_func
) -> str:
    """Get validation error for a FEEDS dict AST node."""
    for key_node, value_node in zip(dict_node.keys, dict_node.values):
        # Root keys may be strings or Path objects
        key_repr = "<?>"
        if isinstance(key_node, ast.Constant):
            key_repr = repr(key_node.value)
            if not isinstance(key_node.value, str):
                return f"key {key_repr} must be a string or Path object"
        elif not (
            isinstance(key_node, ast.Call)
            and isinstance(key_node.func, ast.Name)
            and key_node.func.id == "Path"
        ):
            # Not a string constant or Path() call
            return f"key {key_repr} must be a string or Path object"

        # Feed config must be a dict
        if not isinstance(value_node, ast.Dict):
            # Check if this looks like feed config keys were used at the top level
            if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
                feed_config_keys = {
                    "format",
                    "batch_item_count",
                    "encoding",
                    "fields",
                    "item_classes",
                    "item_filter",
                    "indent",
                    "item_export_kwargs",
                    "overwrite",
                    "store_empty",
                    "uri_params",
                    "postprocessing",
                }
                if key_node.value in feed_config_keys:
                    return f"missing feed URL: {key_repr} appears to be a feed configuration key, but FEEDS must be a dict where keys are feed URLs (like 'output.json') and values are feed configurations"
            return f"feed config for {key_repr} must be a dict"

        # Validate feed config AST
        error = _validate_feed_config_ast(
            key_repr, value_node, feeds_key_versions, get_package_version_func
        )
        if error:
            return error

    return ""


def _validate_feed_config(  # noqa: PLR0911,PLR0912
    feed_key: str,
    feed_config: dict,
    feeds_key_versions: dict[str, str],
    get_package_version_func,
) -> str:
    """Get validation error for a feed config dict value."""
    for key, value in feed_config.items():
        # Feed config keys must be strings
        if not isinstance(key, str):
            return f"feed config key {key!r} in {feed_key!r} must be a string"

        # Check if this is a future key for the current Scrapy version
        if key in feeds_key_versions:
            required_version = feeds_key_versions[key]
            scrapy_version = get_package_version_func("scrapy")
            if scrapy_version is not None and is_version_greater_than(
                required_version, scrapy_version
            ):
                return f"'{key}' in {feed_key!r} is not available in Scrapy {scrapy_version}, requires Scrapy {required_version} or later"

        # Validate specific feed config keys
        if key == "format" and not isinstance(value, str):
            return f"'format' in {feed_key!r} must be a string"
        if key == "batch_item_count" and not (isinstance(value, int) and value >= 0):
            return f"'batch_item_count' in {feed_key!r} must be a non-negative integer"
        if key == "encoding" and value is not None and not isinstance(value, str):
            return f"'encoding' in {feed_key!r} must be a string or None"
        if key == "fields":
            if value is not None:
                if isinstance(value, list):
                    if not all(isinstance(item, str) for item in value):
                        return f"'fields' in {feed_key!r} must be None, a list of strings, or a dict mapping strings to strings"
                elif isinstance(value, dict):
                    if not all(
                        isinstance(k, str) and isinstance(v, str)
                        for k, v in value.items()
                    ):
                        return f"'fields' in {feed_key!r} must be None, a list of strings, or a dict mapping strings to strings"
                else:
                    return f"'fields' in {feed_key!r} must be None, a list of strings, or a dict mapping strings to strings"
        elif key in ("item_classes", "postprocessing"):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        if not looks_like_class_import_path(item):
                            return f"'{key}' in {feed_key!r} contains invalid import path {item!r}"
                    elif not isinstance(item, type):
                        return f"'{key}' in {feed_key!r} must be a list of class objects or class import path strings"
            else:
                return f"'{key}' in {feed_key!r} must be a list of class objects or class import path strings"
        elif key == "item_filter":
            if isinstance(value, str):
                if not looks_like_class_import_path(value):
                    return f"'item_filter' in {feed_key!r} contains invalid import path {value!r}"
            elif not isinstance(value, type):
                return f"'item_filter' in {feed_key!r} must be a class object or class import path string"
        elif key == "indent" and not (isinstance(value, int) and value >= 0):
            return f"'indent' in {feed_key!r} must be a non-negative integer"
        elif key == "item_export_kwargs" and not isinstance(value, dict):
            return f"'item_export_kwargs' in {feed_key!r} must be a dict"
        elif key == "overwrite" and not isinstance(value, bool):
            return f"'overwrite' in {feed_key!r} must be a boolean"
        elif key == "store_empty" and not isinstance(value, bool):
            return f"'store_empty' in {feed_key!r} must be a boolean"
        elif key == "uri_params":
            if isinstance(value, str):
                if not looks_like_callable_import_path(value):
                    return f"'uri_params' in {feed_key!r} contains invalid callable import path {value!r}"
            elif not callable(value):
                return f"'uri_params' in {feed_key!r} must be a callable or callable import path string"

    return ""


def _validate_feed_config_ast(  # noqa: PLR0911,PLR0912
    feed_key: str,
    dict_node: ast.Dict,
    feeds_key_versions: dict[str, str],
    get_package_version_func,
) -> str:
    """Get validation error for a feed config dict AST node."""
    for key_node, value_node in zip(dict_node.keys, dict_node.values):
        if not isinstance(key_node, ast.Constant) or not isinstance(
            key_node.value, str
        ):
            return f"feed config key in {feed_key} must be a string"

        key = key_node.value

        # Check if this is a future key for the current Scrapy version
        if key in feeds_key_versions:
            required_version = feeds_key_versions[key]
            scrapy_version = get_package_version_func("scrapy")
            if scrapy_version is not None and is_version_greater_than(
                required_version, scrapy_version
            ):
                return f"'{key}' in {feed_key} is not available in Scrapy {scrapy_version}, requires Scrapy {required_version} or later"

        # Validate specific feed config keys
        if key == "format":
            if not (
                isinstance(value_node, ast.Constant)
                and isinstance(value_node.value, str)
            ):
                return f"'format' in {feed_key} must be a string"
        elif key == "batch_item_count":
            if not (
                isinstance(value_node, ast.Constant)
                and isinstance(value_node.value, int)
                and value_node.value >= 0
            ):
                return (
                    f"'batch_item_count' in {feed_key} must be a non-negative integer"
                )
        elif key == "encoding":
            if not (
                isinstance(value_node, ast.Constant)
                and (value_node.value is None or isinstance(value_node.value, str))
            ):
                return f"'encoding' in {feed_key} must be a string or None"
        elif key == "fields":
            if isinstance(value_node, ast.Constant) and value_node.value is None:
                pass  # None is valid
            elif isinstance(value_node, ast.List):
                for item_node in value_node.elts:
                    if not (
                        isinstance(item_node, ast.Constant)
                        and isinstance(item_node.value, str)
                    ):
                        return f"'fields' in {feed_key} must be None, a list of strings, or a dict mapping strings to strings"
            elif isinstance(value_node, ast.Dict):
                for k_node, v_node in zip(value_node.keys, value_node.values):
                    if not (
                        isinstance(k_node, ast.Constant)
                        and isinstance(k_node.value, str)
                    ):
                        return f"'fields' in {feed_key} must be None, a list of strings, or a dict mapping strings to strings"
                    if not (
                        isinstance(v_node, ast.Constant)
                        and isinstance(v_node.value, str)
                    ):
                        return f"'fields' in {feed_key} must be None, a list of strings, or a dict mapping strings to strings"
            else:
                return f"'fields' in {feed_key} must be None, a list of strings, or a dict mapping strings to strings"
        elif key in ("item_classes", "postprocessing"):
            if not isinstance(value_node, ast.List):
                return f"'{key}' in {feed_key} must be a list of class objects or class import path strings"
            for item_node in value_node.elts:
                if isinstance(item_node, ast.Constant) and isinstance(
                    item_node.value, str
                ):
                    if not looks_like_class_import_path(item_node.value):
                        return f"'{key}' in {feed_key} contains invalid import path {item_node.value!r}"
                elif not isinstance(
                    item_node, ast.Name
                ):  # Assuming class references are Name nodes
                    return f"'{key}' in {feed_key} must be a list of class objects or class import path strings"
        elif key == "item_filter":
            if isinstance(value_node, ast.Constant) and isinstance(
                value_node.value, str
            ):
                if not looks_like_class_import_path(value_node.value):
                    return f"'item_filter' in {feed_key} contains invalid import path {value_node.value!r}"
            elif not isinstance(
                value_node, ast.Name
            ):  # Assuming class references are Name nodes
                return f"'item_filter' in {feed_key} must be a class object or class import path string"
        elif key == "indent":
            if not (
                isinstance(value_node, ast.Constant)
                and isinstance(value_node.value, int)
                and value_node.value >= 0
            ):
                return f"'indent' in {feed_key} must be a non-negative integer"
        elif key == "item_export_kwargs":
            if not isinstance(value_node, ast.Dict):
                return f"'item_export_kwargs' in {feed_key} must be a dict"
        elif key in ("overwrite", "store_empty"):
            if not (
                isinstance(value_node, ast.Constant)
                and isinstance(value_node.value, bool)
            ):
                return f"'{key}' in {feed_key} must be a boolean"
        elif key == "uri_params":
            if isinstance(value_node, ast.Constant) and isinstance(
                value_node.value, str
            ):
                if not looks_like_callable_import_path(value_node.value):
                    return f"'uri_params' in {feed_key} contains invalid callable import path {value_node.value!r}"
            elif not isinstance(
                value_node, ast.Name
            ):  # Assuming callable references are Name nodes
                return f"'uri_params' in {feed_key} must be a callable or callable import path string"

    return ""


def validate_periodic_log_config(value) -> bool:  # noqa: PLR0911
    """Check if a value is valid for PERIODIC_LOG_DELTA or PERIODIC_LOG_STATS."""
    # Allow None
    if value is None:
        return True

    # Allow True (but not False or other boolean values)
    if value is True:
        return True

    # Allow dict with only 'include' and/or 'exclude' keys
    if isinstance(value, dict):
        # Check that only 'include' and/or 'exclude' keys are present
        allowed_keys = {"include", "exclude"}
        if not set(value.keys()).issubset(allowed_keys):
            return False

        # Check that values are lists of strings
        for val in value.values():
            if not isinstance(val, list):
                return False
            if not all(isinstance(item, str) for item in val):
                return False

        return True

    return False


def validate_periodic_log_config_ast(value_node: ast.AST) -> bool:  # noqa: PLR0911
    """Check if an AST node is invalid for PERIODIC_LOG_DELTA or PERIODIC_LOG_STATS."""
    # Handle constants (None, True, False, strings, etc.)
    if isinstance(value_node, ast.Constant):
        return not validate_periodic_log_config(value_node.value)

    # Handle dictionaries
    if isinstance(value_node, ast.Dict):
        # Check that only 'include' and/or 'exclude' keys are present
        allowed_keys = {"include", "exclude"}
        for key_node in value_node.keys:
            if not isinstance(key_node, ast.Constant) or not isinstance(
                key_node.value, str
            ):
                return True  # Invalid key type
            if key_node.value not in allowed_keys:
                return True  # Invalid key name

        # Check that values are lists
        for value_node_item in value_node.values:
            if not isinstance(value_node_item, ast.List):
                return True  # Value is not a list

            # Check that list items are strings
            for list_item in value_node_item.elts:
                if not isinstance(list_item, ast.Constant) or not isinstance(
                    list_item.value, str
                ):
                    return True  # List item is not a string

        return False  # Valid dict

    # All other types are invalid
    return True


def validate_download_slots_config(value_node: ast.AST) -> str:  # noqa: PLR0911
    """Get specific validation error for DOWNLOAD_SLOTS setting, or empty string if valid."""
    if isinstance(value_node, ast.Constant):
        value = value_node.value
        if isinstance(value, dict):
            return _validate_download_slots_dict(value)
        if isinstance(value, str):
            try:
                parsed_value = json.loads(value)
                if not isinstance(parsed_value, dict):
                    return "must be a dict"
                return _validate_download_slots_dict(parsed_value)
            except (json.JSONDecodeError, TypeError):
                return "must be a dict"
        else:
            return "must be a dict"

    if isinstance(value_node, ast.Dict):
        return _validate_download_slots_dict_ast(value_node)

    return "must be a dict"


def _validate_download_slots_dict(slots_dict: dict) -> str:
    """Get validation error for a DOWNLOAD_SLOTS dict value at runtime."""
    for key, slot_config in slots_dict.items():
        if not isinstance(key, str):
            return f"key {key!r} must be a string"

        if not isinstance(slot_config, dict):
            return f"slot config for {key!r} must be a dict"

        error = _validate_slot_config(key, slot_config)
        if error:
            return error

    return ""


def _validate_download_slots_dict_ast(dict_node: ast.Dict) -> str:
    """Get validation error for a DOWNLOAD_SLOTS dict AST node."""
    for key_node, value_node in zip(dict_node.keys, dict_node.values):
        key_repr = "<?>"
        if isinstance(key_node, ast.Constant):
            key_repr = repr(key_node.value)
            if not isinstance(key_node.value, str):
                return f"key {key_repr} must be a string"
        else:
            return f"key {key_repr} must be a string"

        if not isinstance(value_node, ast.Dict):
            return f"slot config for {key_repr} must be a dict"

        error = _validate_slot_config_ast(key_repr, value_node)
        if error:
            return error

    return ""


def _validate_slot_config(slot_key: str, slot_config: dict) -> str:
    """Get validation error for a slot config dict value."""
    allowed_keys = {"concurrency", "delay", "randomize_delay"}
    for key, value in slot_config.items():
        if not isinstance(key, str):
            return f"slot config key {key!r} in {slot_key!r} must be a string"

        if key not in allowed_keys:
            return f"unknown slot config key '{key}' in {slot_key!r}, must be one of: {', '.join(sorted(allowed_keys))}"

        if key == "concurrency" and not (isinstance(value, int) and value >= 1):
            return f"'concurrency' in {slot_key!r} must be a positive integer (1+)"
        if key == "delay" and not (isinstance(value, (int, float)) and value >= 0.0):
            return f"'delay' in {slot_key!r} must be a positive float (0.0+)"
        if key == "randomize_delay" and not isinstance(value, bool):
            return f"'randomize_delay' in {slot_key!r} must be a boolean"

    return ""


def _validate_slot_config_ast(slot_key: str, dict_node: ast.Dict) -> str:
    """Get validation error for a slot config dict AST node."""
    allowed_keys = {"concurrency", "delay", "randomize_delay"}
    for key_node, value_node in zip(dict_node.keys, dict_node.values):
        if not isinstance(key_node, ast.Constant) or not isinstance(
            key_node.value, str
        ):
            return f"slot config key in {slot_key} must be a string"

        key = key_node.value

        if key not in allowed_keys:
            return f"unknown slot config key '{key}' in {slot_key}, must be one of: {', '.join(sorted(allowed_keys))}"

        if key == "concurrency":
            if not (
                isinstance(value_node, ast.Constant)
                and isinstance(value_node.value, int)
                and value_node.value >= 1
            ):
                return f"'concurrency' in {slot_key} must be a positive integer (1+)"
        elif key == "delay":
            if not (
                isinstance(value_node, ast.Constant)
                and isinstance(value_node.value, (int, float))
                and value_node.value >= 0.0
            ):
                return f"'delay' in {slot_key} must be a positive float (0.0+)"
        elif key == "randomize_delay" and not (
            isinstance(value_node, ast.Constant) and isinstance(value_node.value, bool)
        ):
            return f"'randomize_delay' in {slot_key} must be a boolean"

    return ""


def get_enum_validation_error(
    setting_name: str, enum_settings: dict[str, list[str]]
) -> str:
    """Get enum validation error message for a setting."""
    if setting_name in enum_settings:
        allowed_values = ", ".join(f"'{v}'" for v in enum_settings[setting_name])
        return f"only supports the following values: {allowed_values}."
    return "only supports specific string values."
