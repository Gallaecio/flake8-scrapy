from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from . import MINIMUM_SUPPORTED_SCRAPY_VERSION, IssueFinder
from .mixins import RequirementsParsingMixin, VersionValidationMixin
from .utilities import (
    is_frozen_requirement,
)

if TYPE_CHECKING:
    from collections.abc import Generator


class BaseProjectIssueFinder(IssueFinder, RequirementsParsingMixin):
    def __init__(self, filename=None, *args, **kwargs):
        super().__init__(*args, filename=filename, **kwargs)
        self._checked_projects = set()

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
        req = self.parse_requirement_from_line(line)
        if req is not None and not is_frozen_requirement(req):
            message = f"{self.msg_code} {self.msg_info}: {req.name}"
            yield (line_num, 0, message)


class BaseScrapyVersionIssueFinder(BaseProjectIssueFinder, VersionValidationMixin):
    """Base class for Scrapy version checkers."""

    minimum_version: str = ""

    def check_requirement_line(
        self, line_num: int, line: str
    ) -> Generator[tuple[int, int, str], None, None]:
        req = self.parse_requirement_from_line(line)
        if req is None:
            return
        yield from self.validate_scrapy_version(req, line_num)


class AncientScrapyVersionIssueFinder(BaseScrapyVersionIssueFinder):
    msg_code = "SCP13"
    msg_info = "ancient Scrapy version in requirements.txt"
    minimum_version = MINIMUM_SUPPORTED_SCRAPY_VERSION


class InsecureScrapyVersionIssueFinder(BaseScrapyVersionIssueFinder):
    msg_code = "SCP14"
    msg_info = "insecure Scrapy version in requirements.txt"
    minimum_version = "2.11.2"


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
        req = self.parse_requirement_from_line(line)
        if req is None:
            return

        package_name = req.name.lower()
        if package_name in self.OBSOLETE_PACKAGES:
            replacements = self.OBSOLETE_PACKAGES[package_name]
            replacement_text = (
                replacements[0] if len(replacements) == 1 else " or ".join(replacements)
            )
            message = f"{self.msg_code} {self.msg_info}: {req.name} (use {replacement_text} instead)"
            yield (line_num, 0, message)
