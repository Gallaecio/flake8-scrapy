from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from packaging.version import InvalidVersion, Version

from . import MINIMUM_SUPPORTED_SCRAPY_VERSION, IssueFinder

if TYPE_CHECKING:
    from collections.abc import Generator


class BaseProjectIssueFinder(IssueFinder):
    def __init__(self, filename=None, *args, **kwargs):
        super().__init__(*args, filename=filename, **kwargs)
        self._checked_projects = set()

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
        return
        yield

    def find_issues(self, node) -> Generator[tuple[int, int, str], None, None]:
        yield from self.process_requirements_txt(node)


class RequirementsTxtIssueFinder(BaseProjectIssueFinder):
    msg_code = "SCP11"
    msg_info = "missing requirements.txt"

    def check_missing_requirements(self) -> Generator[tuple[int, int, str], None, None]:
        yield (1, 0, self.message)


class NonFrozenDependenciesIssueFinder(BaseProjectIssueFinder):
    msg_code = "SCP12"
    msg_info = "non-frozen dependency in requirements.txt"

    def check_requirement_line(
        self, line_num: int, line: str
    ) -> Generator[tuple[int, int, str], None, None]:
        req = self.parse_requirement_line(line)
        if req is not None and not self.is_frozen_requirement(req):
            message = f"{self.msg_code} {self.msg_info}: {req.name}"
            yield (line_num, 0, message)


class AncientScrapyVersionIssueFinder(BaseProjectIssueFinder):
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
            if self.is_version_less_than(
                version_part, MINIMUM_SUPPORTED_SCRAPY_VERSION
            ):
                message = f"{self.msg_code} {self.msg_info}: {version_part} (minimum required: {MINIMUM_SUPPORTED_SCRAPY_VERSION})"
                yield (line_num, 0, message)


class InsecureScrapyVersionIssueFinder(BaseProjectIssueFinder):
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


class ObsoletePackagesIssueFinder(BaseProjectIssueFinder):
    msg_code = "SCP16"
    msg_info = "obsolete package in requirements.txt"

    OBSOLETE_PACKAGES: ClassVar[dict[str, list[str]]] = {
        "scrapy-crawlera": ["scrapy-zyte-smartproxy"],
        "scrapy-splash": ["scrapy-zyte-api", "scrapy-playwright"],
    }

    def check_requirement_line(
        self, line_num: int, line: str
    ) -> Generator[tuple[int, int, str], None, None]:
        req = self.parse_requirement_line(line)
        if req is None:
            return

        package_name = req.name.lower()
        if package_name in self.OBSOLETE_PACKAGES:
            replacements = self.OBSOLETE_PACKAGES[package_name]
            if len(replacements) == 1:
                replacement_text = replacements[0]
            else:
                replacement_text = " or ".join(replacements)

            message = f"{self.msg_code} {self.msg_info}: {req.name} (use {replacement_text} instead)"
            yield (line_num, 0, message)
