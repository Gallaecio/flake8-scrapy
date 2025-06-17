from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Generator

    from flake8_scrapy.issues import Issue


class IssueFinder(Protocol):
    visit_types: tuple[str, ...]

    def find_issues(self, node) -> Generator[Issue, None, None]: ...
