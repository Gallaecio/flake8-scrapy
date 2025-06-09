from __future__ import annotations

from typing import TYPE_CHECKING

from .utilities import (
    extract_version_from_requirement,
    format_version_issue_message,
    is_frozen_requirement,
    is_version_less_than,
    parse_requirement_line,
)

if TYPE_CHECKING:
    from collections.abc import Generator

    from packaging.requirements import Requirement


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
