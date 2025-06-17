from __future__ import annotations

from ast import AST, NodeVisitor
from collections import defaultdict
from typing import TYPE_CHECKING, ClassVar

from .context import Context
from .finders.domains import (
    UnreachableDomainIssueFinder,
    UrlInAllowedDomainsIssueFinder,
)
from .finders.oldstyle import OldSelectorIssueFinder, UrlJoinIssueFinder
from .finders.settings import SettingsIssueFinder

__version__ = "0.0.2"

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence

    from flake8_scrapy.finders import IssueFinder

    from .issues import Issue


class ScrapyStyleIssueFinder(NodeVisitor):
    def __init__(self, context: Context):
        super().__init__()
        self.context = context
        self.issues: list[Issue] = []
        self.load_finders(context)

    def load_finders(self, context: Context):
        self.finders: defaultdict[str, list[IssueFinder]] = defaultdict(list)
        for finder in (
            UnreachableDomainIssueFinder(),
            UrlInAllowedDomainsIssueFinder(),
            OldSelectorIssueFinder(),
            UrlJoinIssueFinder(),
            SettingsIssueFinder(context),
        ):
            for visit_type in finder.visit_types:
                self.finders[visit_type].append(finder)

    def check(self) -> Generator[Issue, None, None]:
        assert self.context.file.tree is not None
        self.visit(self.context.file.tree)
        yield from self.issues

    def find_issues_visitor(self, visitor_type: str, node):
        for finder in self.finders[visitor_type]:
            for issue in finder.find_issues(node):
                self.issues.append(issue)
        self.generic_visit(node)

    def visit_Assign(self, node):
        self.find_issues_visitor("Assign", node)

    def visit_Call(self, node):
        self.find_issues_visitor("Call", node)

    def visit_Subscript(self, node):
        self.find_issues_visitor("Subscript", node)


class ScrapyStyleChecker:
    options = None
    name = "flake8-scrapy"
    version = __version__
    requirements_file_path: ClassVar[str] = ""

    @classmethod
    def add_options(cls, parser):
        parser.add_option(
            "--scrapy-requirements-file",
            default="",
            help="Path of the project requirements file",
            parse_from_config=True,
        )

    @classmethod
    def parse_options(cls, options):
        if not options:
            return
        cls.requirements_file_path = options.scrapy_requirements_file or getattr(
            options, "requirements_file", ""
        )

    def __init__(
        self, tree: AST | None, filename: str, lines: Sequence[str] | None = None
    ):
        self.tree = tree
        context = Context.from_flake8_params(
            tree, filename, lines, self.requirements_file_path
        )
        self.code_finder = ScrapyStyleIssueFinder(context)

    def run(self):
        for issue in self.run_checks():
            yield (*issue, self.__class__)

    def run_checks(self):
        if self.tree:
            yield from self.code_finder.check()
