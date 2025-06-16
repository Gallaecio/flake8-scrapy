from __future__ import annotations

from typing import TYPE_CHECKING

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

from flake8_scrapy.issues import Issue

if TYPE_CHECKING:
    from collections.abc import Generator

    from flake8_scrapy.context import Context


class RequirementsIssueFinder:
    REQUIRED_DEPENDENCIES = frozenset(
        {
            "cryptography",
            "cssselect",
            "lxml",
            "parsel",
            "protego",
            "pyopenssl",
            "queuelib",
            "service-identity",
            "twisted",
            "w3lib",
            "zope-interface",
        }
    )

    def __init__(self, context: Context):
        self.context = context

    def in_requirements_file(self) -> bool:
        if not self.context.project.requirements_file_path:
            return False
        return self.context.file.path == self.context.project.requirements_file_path

    def check(self) -> Generator[Issue, None, None]:
        if not self.context.file.lines:
            yield Issue(13, "incomplete requirements freeze")
            return
        packages = set()
        for line in self.context.file.lines:
            line = line.strip()  # noqa: PLW2901
            if not line or line.startswith("#"):
                continue
            if line.startswith("-e"):
                yield Issue(13, "incomplete requirements freeze")
                return
            try:
                requirement = Requirement(line)
            except InvalidRequirement:
                continue
            normalized = canonicalize_name(requirement.name)
            packages.add(normalized)
        missing_deps = self.REQUIRED_DEPENDENCIES - packages
        if missing_deps or not packages:
            yield Issue(13, "incomplete requirements freeze")
