from __future__ import annotations

import ast
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator

    from flake8_scrapy.context import Context
    from flake8_scrapy.issues import Issue


class SettingsIssueFinder:
    visit_types: tuple[str, ...] = ("Assign", "Call", "Subscript")

    def __init__(self, context: Context | None = None):
        self.context = context

    def find_issues(self, node) -> Generator[Issue, None, None]:
        if isinstance(node, ast.Assign):
            yield from self.find_assign_issues(node)
        elif isinstance(node, ast.Call):
            yield from self.find_call_issues(node)
        elif isinstance(node, ast.Subscript):
            yield from self.find_subscript_issues(node)

    def find_assign_issues(self, node: ast.Assign) -> Generator[Issue, None, None]:
        return
        yield

    def find_call_issues(self, node: ast.Call) -> Generator[Issue, None, None]:
        return
        yield

    def find_subscript_issues(
        self, node: ast.Subscript
    ) -> Generator[Issue, None, None]:
        return
        yield
