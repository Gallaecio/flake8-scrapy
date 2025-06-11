from __future__ import annotations

from abc import abstractmethod
from configparser import ConfigParser
from importlib.util import find_spec
from pathlib import Path
from typing import TYPE_CHECKING

from packaging.requirements import InvalidRequirement, Requirement

if TYPE_CHECKING:
    from collections.abc import Generator


import sys
from contextlib import contextmanager


@contextmanager
def extend_sys_path(path):
    original_sys_path = sys.path.copy()
    sys.path.insert(0, path)
    try:
        yield
    finally:
        sys.path = original_sys_path


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
            if (parent / "scrapy.cfg").exists():
                return parent
        return None

    def file_is_settings_module(self) -> bool:
        if not self.filename:
            return False
        root = self.get_project_root()
        if not root:
            return False
        config_file = root / "scrapy.cfg"
        config = ConfigParser()
        config.read(config_file)
        if "settings" not in config:
            return False
        file_path = Path(self.filename).resolve()
        with extend_sys_path(str(root.resolve())):
            for module in config["settings"].values():
                spec = find_spec(module)
                if not spec or not spec.origin:
                    continue
                module_path = Path(spec.origin).resolve()
                if module_path == file_path:
                    return True
        return False

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
