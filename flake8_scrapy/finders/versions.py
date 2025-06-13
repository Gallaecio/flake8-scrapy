from __future__ import annotations

from typing import TYPE_CHECKING

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

from .messaging import (
    format_version_issue_message,
)

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path


class VersionValidationMixin:
    """Mixin for validating version requirements."""

    def check_version_requirement(
        self, req: Requirement, line_num: int, package_name: str, minimum_version: str
    ) -> Generator[tuple[int, int, str], None, None]:
        """Generic version validation for any package."""
        if req.name.lower() == package_name.lower() and is_frozen_requirement(req):
            version_part = extract_version_from_requirement(req)
            if version_part and is_version_less_than(version_part, minimum_version):
                message = format_version_issue_message(
                    self.msg_code, self.msg_info, version_part, minimum_version
                )
                yield (line_num, 0, message)


class RequirementsParsingMixin:
    """Mixin for parsing and processing requirements.txt files."""

    def should_check_project(self, project_root) -> bool:
        """Check if project should be processed (avoid duplicate checks)."""
        if not project_root:
            return False
        project_key = str(project_root)
        if project_key in self._checked_projects:
            return False
        self._checked_projects.add(project_key)
        return True

    def process_requirements_txt(
        self, node
    ) -> Generator[tuple[int, int, str], None, None]:
        """Process requirements.txt file and yield issues for each line."""
        project_root = self.get_project_root()
        if not self.should_check_project(project_root):
            return
        assert project_root is not None
        requirements_txt = project_root / "requirements.txt"

        if (
            hasattr(self, "check_missing_requirements")
            and not requirements_txt.exists()
        ):
            yield from self.check_missing_requirements()
            return

        if not requirements_txt.exists():
            return

        try:
            content = requirements_txt.read_text(encoding="utf-8")
            lines = content.splitlines()
            for line_num, line in enumerate(lines, 1):
                yield from self.check_requirement_line(line_num, line)
        except (OSError, UnicodeDecodeError):
            # If we can't read the file, skip the check
            return

    def check_requirement_line(
        self, line_num: int, line: str
    ) -> Generator[tuple[int, int, str], None, None]:
        """Override this method to implement specific requirement line checks."""
        return
        yield

    def parse_requirement_from_line(self, line: str) -> Requirement | None:
        """Parse a requirement line and return a Requirement object if valid."""
        return parse_requirement_line(line)


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
