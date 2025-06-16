from __future__ import annotations

import re
from typing import TYPE_CHECKING

import yaml

from flake8_scrapy.issues import Issue

if TYPE_CHECKING:
    from collections.abc import Generator

    from flake8_scrapy.context import Context


class ScrapinghubIssueFinder:
    def __init__(self, context: Context):
        self.context = context

    def in_scrapinghub_file(self) -> bool:
        if not self.context.project.root:
            return False
        return self.context.file.path == self.context.project.root / "scrapinghub.yml"

    def check(self) -> Generator[Issue, None, None]:
        assert self.context.file.lines is not None
        content = "\n".join(self.context.file.lines)
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError:
            return
        if not isinstance(data, dict):
            return
        if self._has_image_key(data):
            return
        if "stack" not in data:
            yield Issue(18, "no root stack")
        yield from self.check_stacks(data)

    def check_stacks(
        self, data: dict, path: list[str] | None = None
    ) -> Generator[Issue, None, None]:
        if path is None:
            path = []
        for key, value in data.items():
            current_path = [*path, key]
            if key == "stack":
                if len(current_path) > 1:
                    yield Issue(19, "non-root stack")
                if not self._is_frozen_stack(value):
                    yield Issue(20, "stack not frozen")
            if isinstance(value, dict):
                yield from self.check_stacks(value, current_path)

    def _is_frozen_stack(self, stack: str) -> bool:
        return isinstance(stack, str) and bool(re.search(r"-\d{8}$", stack))

    def _has_image_key(self, data: dict, path: list[str] | None = None) -> bool:
        if path is None:
            path = []
        for key, value in data.items():
            if key == "image":
                return True
            if isinstance(value, dict) and self._has_image_key(value, [*path, key]):
                return True
        return False
