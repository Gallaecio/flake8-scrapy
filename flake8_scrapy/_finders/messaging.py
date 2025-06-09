from __future__ import annotations


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


def get_enum_validation_error(
    setting_name: str, enum_settings: dict[str, list[str]]
) -> str:
    """Get enum validation error message for a setting."""
    if setting_name in enum_settings:
        allowed_values = ", ".join(f"'{v}'" for v in enum_settings[setting_name])
        return f"only supports the following values: {allowed_values}."
    return "only supports specific string values."
