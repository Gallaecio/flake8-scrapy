from __future__ import annotations

from ast import AST, NodeVisitor
from typing import TYPE_CHECKING

from .context import Context
from .finders.domains import (
    UnreachableDomainIssueFinder,
    UrlInAllowedDomainsIssueFinder,
)
from .finders.oldstyle import OldSelectorIssueFinder, UrlJoinIssueFinder
from .finders.setting_modules import SettingModuleIssueFinder

__version__ = "0.0.2"

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence


class ScrapyStyleIssueFinder(NodeVisitor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.issues = []
        self.finders: dict[str, Sequence] = {
            "Assign": [
                UnreachableDomainIssueFinder(),
                UrlInAllowedDomainsIssueFinder(),
                OldSelectorIssueFinder(),
            ],
            "Call": [
                UrlJoinIssueFinder(),
            ],
        }

    def find_issues_visitor(self, visitor, node):
        """Find issues for the provided visitor"""
        for finder in self.finders[visitor]:
            issues = finder.find_issues(node)
            if issues:
                self.issues.extend(list(issues))
        self.generic_visit(node)

    def visit_Assign(self, node):
        self.find_issues_visitor("Assign", node)

    def visit_Call(self, node):
        self.find_issues_visitor("Call", node)


class ScrapyStyleChecker:
    options = None
    name = "flake8-scrapy"
    version = __version__

    def __init__(self, tree: AST | None, filename: str):
        self.tree = tree
        context = Context.from_flake8_params(tree, filename)
        self.setting_module_finder = SettingModuleIssueFinder(context)

    def run(self):
        for issue in self.run_checks():
            yield (*issue, self.__class__)

    def run_checks(self):
        if self.setting_module_finder.in_setting_module():
            yield from self.setting_module_finder.check()
        elif self.tree:
            yield from self.check_code()

    def check_code(self) -> Generator[tuple[str, int, int], None, None]:
        finder = ScrapyStyleIssueFinder()
        assert self.tree is not None
        finder.visit(self.tree)
        yield from finder.issues
