from __future__ import annotations

import ast
from typing import TYPE_CHECKING, TypedDict

from flake8_scrapy.issues import Issue

if TYPE_CHECKING:
    from collections.abc import Generator

    from flake8_scrapy.context import Context


class Location(TypedDict):
    line: int
    column: int


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
        if isinstance(node.func, ast.Attribute):
            if self.is_settings_object(node.func.value):
                if self.is_defaultless_getter_call(node):
                    yield Issue(
                        code=28,
                        summary="unneeded setting get",
                        **self.get_method_location(node),
                    )

    def find_subscript_issues(
        self, node: ast.Subscript
    ) -> Generator[Issue, None, None]:
        return
        yield

    def get_method_location(self, node: ast.Call) -> Location:
        assert isinstance(node.func, ast.Attribute)
        assert node.func.value.end_col_offset is not None
        return {
            "line": node.func.lineno,
            "column": node.func.value.end_col_offset + 1,
        }

    def is_defaultless_getter_call(self, node: ast.Call) -> bool:
        assert isinstance(node.func, ast.Attribute)
        return node.func.attr == "get" and (
            (len(node.args) == 1 and len(node.keywords) == 0)
            or (
                not len(node.args)
                and len(node.keywords) == 1
                and node.keywords[0].arg == "name"
            )
        )

    def is_settings_object(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Name):
            return node.id == "settings"
        if isinstance(node, ast.Attribute):
            return node.attr == "settings"
        return False
