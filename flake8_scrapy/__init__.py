import ast

from ._finders.domains import (
    UnreachableDomainIssueFinder,
    UrlInAllowedDomainsIssueFinder,
)
from ._finders.oldstyle import OldSelectorIssueFinder, UrlJoinIssueFinder
from ._finders.settings import (
    DeprecatedSettingsIssueFinder,
    FutureSettingsIssueFinder,
    RemovedSettingsIssueFinder,
    UnknownSettingsIssueFinder,
)

__version__ = "0.0.2"


class ScrapyStyleIssueFinder(ast.NodeVisitor):
    def __init__(self, filename=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.issues = []
        setting_finders = (
            DeprecatedSettingsIssueFinder(filename),
            FutureSettingsIssueFinder(filename),
            RemovedSettingsIssueFinder(filename),
            UnknownSettingsIssueFinder(filename),
        )
        self.finders = {
            "Assign": [
                UnreachableDomainIssueFinder(),
                UrlInAllowedDomainsIssueFinder(),
                OldSelectorIssueFinder(),
                *setting_finders,
            ],
            "Call": [
                UrlJoinIssueFinder(),
                *setting_finders,
            ],
            "Subscript": [
                *setting_finders,
            ],
            "ClassDef": [
                *setting_finders,
            ],
            "Delete": [
                *setting_finders,
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

    def visit_Subscript(self, node):
        self.find_issues_visitor("Subscript", node)

    def visit_ClassDef(self, node):
        self.find_issues_visitor("ClassDef", node)

    def visit_Delete(self, node):
        self.find_issues_visitor("Delete", node)


class ScrapyStyleChecker:
    options = None
    name = "flake8-scrapy"
    version = __version__

    def __init__(self, tree, filename):
        self.tree = tree
        self.filename = filename

    def run(self):
        finder = ScrapyStyleIssueFinder(self.filename)
        finder.visit(self.tree)

        for line, col, msg in finder.issues:
            yield (line, col, msg, ScrapyStyleChecker)
