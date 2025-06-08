from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from packaging.requirements import InvalidRequirement, Requirement
from packaging.version import InvalidVersion, Version

from . import IssueFinder

if TYPE_CHECKING:
    from collections.abc import Generator


class ProjectIssueFinder(IssueFinder):
    def __init__(self, filename=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filename = filename
        self._checked_projects = set()

    def get_project_root(self, filepath):
        if not filepath:
            return None
        path = Path(filepath).resolve()
        for parent in [path, *list(path.parents)]:
            indicators = [
                "scrapy.cfg",
                "pyproject.toml",
                "setup.py",
                "setup.cfg",
                ".git",
                "scrapinghub.yml",
                "requirements.txt",
            ]
            if any((parent / indicator).exists() for indicator in indicators):
                return parent
        # If no indicators are found, use the directory containing the file
        return path.parent if path.is_file() else path

    def should_check_project(self, project_root):
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
        if not self.filename:
            return
        project_root = self.get_project_root(self.filename)
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

    def parse_requirement_line(self, line: str) -> Requirement | None:
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

    def is_frozen_requirement(self, req: Requirement) -> bool:
        return len(req.specifier) == 1 and next(iter(req.specifier)).operator == "=="

    def check_requirement_line(
        self, line_num: int, line: str
    ) -> Generator[tuple[int, int, str], None, None]:
        return
        yield

    def find_issues(self, node) -> Generator[tuple[int, int, str], None, None]:
        yield from self.process_requirements_txt(node)


class RequirementsTxtIssueFinder(ProjectIssueFinder):
    msg_code = "SCP11"
    msg_info = "missing requirements.txt"

    def check_missing_requirements(self) -> Generator[tuple[int, int, str], None, None]:
        yield (1, 0, self.message)


class NonFrozenDependenciesIssueFinder(ProjectIssueFinder):
    msg_code = "SCP12"
    msg_info = "non-frozen dependency in requirements.txt"

    def check_requirement_line(
        self, line_num: int, line: str
    ) -> Generator[tuple[int, int, str], None, None]:
        req = self.parse_requirement_line(line)
        if req is not None and not self.is_frozen_requirement(req):
            message = f"{self.msg_code} {self.msg_info}: {req.name}"
            yield (line_num, 0, message)


class AncientScrapyVersionIssueFinder(ProjectIssueFinder):
    msg_code = "SCP13"
    msg_info = "ancient Scrapy version in requirements.txt"

    def is_version_less_than(self, version, min_version):
        try:
            return Version(version) < Version(min_version)
        except InvalidVersion:
            return False

    def check_requirement_line(
        self, line_num: int, line: str
    ) -> Generator[tuple[int, int, str], None, None]:
        req = self.parse_requirement_line(line)
        if req is None:
            return
        if req.name.lower() == "scrapy" and self.is_frozen_requirement(req):
            version_part = next(iter(req.specifier)).version
            if self.is_version_less_than(version_part, "2.0.1"):
                message = f"{self.msg_code} {self.msg_info}: {version_part} (minimum required: 2.0.1)"
                yield (line_num, 0, message)


class InsecureScrapyVersionIssueFinder(ProjectIssueFinder):
    msg_code = "SCP14"
    msg_info = "insecure Scrapy version in requirements.txt"

    def is_version_less_than(self, version, min_version):
        try:
            return Version(version) < Version(min_version)
        except InvalidVersion:
            return False

    def check_requirement_line(
        self, line_num: int, line: str
    ) -> Generator[tuple[int, int, str], None, None]:
        req = self.parse_requirement_line(line)
        if req is None:
            return
        if req.name.lower() == "scrapy" and self.is_frozen_requirement(req):
            version_part = next(iter(req.specifier)).version
            if self.is_version_less_than(version_part, "2.11.2"):
                message = f"{self.msg_code} {self.msg_info}: {version_part} (minimum required: 2.11.2)"
                yield (line_num, 0, message)
