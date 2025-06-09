from __future__ import annotations

from typing import TYPE_CHECKING

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

if TYPE_CHECKING:
    from pathlib import Path


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


def is_version_less_than(version: str, min_version: str) -> bool:
    """Compare two version strings, returning True if version < min_version."""
    try:
        return Version(version) < Version(min_version)
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
