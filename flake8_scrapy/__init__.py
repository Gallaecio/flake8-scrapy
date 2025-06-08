import ast
from typing import ClassVar

from ._finders.domains import (
    UnreachableDomainIssueFinder,
    UrlInAllowedDomainsIssueFinder,
)
from ._finders.oldstyle import OldSelectorIssueFinder, UrlJoinIssueFinder
from ._finders.project import (
    AncientScrapyVersionIssueFinder,
    InsecureScrapyVersionIssueFinder,
    NonFrozenDependenciesIssueFinder,
    RequirementsTxtIssueFinder,
)
from ._finders.settings import (
    DeprecatedSettingsIssueFinder,
    FutureSettingsIssueFinder,
    MissingPackageSettingsIssueFinder,
    RemovedSettingsIssueFinder,
    UnknownSettingsIssueFinder,
)

__version__ = "0.0.2"


class IssueReporter(ast.NodeVisitor):
    def __init__(
        self,
        filename=None,
        allowed_settings=None,
        enable_project_checks=True,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.issues = []
        # MissingPackageSettingsIssueFinder must be first to have priority
        missing_package_finder = MissingPackageSettingsIssueFinder(
            filename, allowed_settings=allowed_settings
        )

        # Get settings that are missing packages to exclude from other checks
        missing_package_settings = missing_package_finder.missing_package_settings

        setting_finders = (
            missing_package_finder,
            DeprecatedSettingsIssueFinder(
                filename,
                allowed_settings=allowed_settings,
                exclude_settings=missing_package_settings,
            ),
            FutureSettingsIssueFinder(
                filename,
                allowed_settings=allowed_settings,
                exclude_settings=missing_package_settings,
            ),
            RemovedSettingsIssueFinder(
                filename,
                allowed_settings=allowed_settings,
                exclude_settings=missing_package_settings,
            ),
            UnknownSettingsIssueFinder(
                filename,
                allowed_settings=allowed_settings,
                exclude_settings=missing_package_settings,
            ),
        )
        project_finders = []
        if enable_project_checks:
            project_finders = [
                RequirementsTxtIssueFinder(filename),
                NonFrozenDependenciesIssueFinder(filename),
                AncientScrapyVersionIssueFinder(filename),
                InsecureScrapyVersionIssueFinder(filename),
            ]
        self.finders = {
            "Assign": [
                UnreachableDomainIssueFinder(),
                UrlInAllowedDomainsIssueFinder(),
                OldSelectorIssueFinder(),
                *setting_finders,
                *project_finders,
            ],
            "Call": [
                UrlJoinIssueFinder(),
                *setting_finders,
                *project_finders,
            ],
            "Subscript": [
                *setting_finders,
                *project_finders,
            ],
            "ClassDef": [
                *setting_finders,
                *project_finders,
            ],
            "Delete": [
                *setting_finders,
                *project_finders,
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


class Plugin:
    options = None
    name = "flake8-scrapy"
    version = __version__
    allowed_settings: ClassVar[list[str]] = []

    @classmethod
    def add_options(cls, parser):
        parser.add_option(  # pragma: no cover
            "--allow-scrapy-settings",
            default="",
            help="Comma-separated list of Scrapy settings to always allow (default: empty)",
            parse_from_config=True,
        )

    @classmethod
    def parse_options(cls, options):
        cls.parse_allowed_settings(options)

    @classmethod
    def parse_allowed_settings(cls, options):
        if not options:  # pragma: no cover
            return
        if not options.allow_scrapy_settings:
            return
        cls.allowed_settings = [
            setting.strip()
            for setting in options.allow_scrapy_settings.split(",")
            if setting.strip()
        ]

    def __init__(self, tree, filename, enable_project_checks=True):
        self.tree = tree
        self.filename = filename
        self.enable_project_checks = enable_project_checks

    def run(self):
        reporter = IssueReporter(
            self.filename,
            allowed_settings=self.allowed_settings,
            enable_project_checks=self.enable_project_checks,
        )
        reporter.visit(self.tree)
        for line, col, msg in reporter.issues:
            yield (line, col, msg, Plugin)
