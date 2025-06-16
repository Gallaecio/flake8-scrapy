from __future__ import annotations

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
        if "stack" not in data:
            yield Issue(18, "no root stack")
        yield from self.check_nested_stacks(data)

    def check_nested_stacks(
        self, data: dict, path: list[str] | None = None
    ) -> Generator[Issue, None, None]:
        if path is None:
            path = []
        for key, value in data.items():
            current_path = [*path, key]
            if key == "stack" and len(current_path) > 1:
                yield Issue(19, "non-root stack")
            if isinstance(value, dict):
                yield from self.check_nested_stacks(value, current_path)
