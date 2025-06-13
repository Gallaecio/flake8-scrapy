from collections.abc import Generator
from pathlib import Path

from packaging.version import Version

from .finders.data import (
    MIN_SAFE_SCRAPY_VERSION,
    MIN_SCRAPY_VERSION,
    OBSOLETE_PACKAGES,
)
from .finders.messaging import Issue
from .finders.versions import is_frozen_requirement, parse_requirement_line


def check_requirements(
    file_path: str, lines: list[str]
) -> Generator[Issue, None, None]:
    if not (Path(file_path).parent / "scrapy.cfg").exists():
        return
    seen = {}
    for line_num, line in enumerate(lines, start=1):
        requirement = parse_requirement_line(line)
        if requirement is None:
            continue
        name = requirement.name.lower()
        if name in seen:
            yield Issue(
                11,
                "duplicate dependency",
                f"first seen on line {seen[name]}",
                line=line_num,
            )
            continue
        seen[name] = line_num
        if not is_frozen_requirement(requirement):
            yield Issue(12, "non-frozen dependency", line=line_num)
            continue
        if name == "scrapy":
            version = Version(next(iter(requirement.specifier)).version)
            if version < MIN_SCRAPY_VERSION:
                yield Issue(13, "ancient Scrapy", line=line_num)
            elif version < MIN_SAFE_SCRAPY_VERSION:
                yield Issue(14, "unsafe Scrapy", line=line_num)
        elif name in OBSOLETE_PACKAGES:
            yield Issue(16, "obsolete package", line=line_num)
