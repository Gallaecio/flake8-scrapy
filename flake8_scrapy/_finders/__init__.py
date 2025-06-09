from __future__ import annotations

from abc import abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from packaging.requirements import InvalidRequirement, Requirement

if TYPE_CHECKING:
    from collections.abc import Generator


class IssueFinder:
    msg_code = ""
    msg_info = ""

    def __init__(self, filename=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filename = filename

    @property
    def message(self):
        return f"{self.msg_code} {self.msg_info}"

    @abstractmethod
    def find_issues(self, node) -> Generator[tuple[int, int, str], None, None]:
        pass

    def get_project_root(self):
        if not self.filename:
            return None
        path = Path(self.filename).resolve()
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
            for indicator in indicators:
                if (parent / indicator).exists():
                    return parent
        # If no indicators are found, use the directory containing the file
        return path.parent if path.is_file() else path

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
