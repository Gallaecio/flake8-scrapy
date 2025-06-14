from __future__ import annotations

from typing import TYPE_CHECKING

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

if TYPE_CHECKING:
    from pathlib import Path


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
