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
    ObsoletePackagesIssueFinder,
    RequirementsTxtIssueFinder,
)
from ._finders.settings import (
    BaseSettingNameIssueFinder,
    DeprecatedSettingsIssueFinder,
    DuplicateSettingsIssueFinder,
    FutureSettingsIssueFinder,
    IgnoredGetDefaultIssueFinder,
    InvalidValueSettingsIssueFinder,
    MissingPackageSettingsIssueFinder,
    MissingUserAgentIssueFinder,
    RemovedSettingsIssueFinder,
    RobotsTxtObeyIssueFinder,
    ThrottlingConfigIssueFinder,
    TypeMismatchSettingsIssueFinder,
    UnknownSettingsIssueFinder,
    UnnecessaryGetIssueFinder,
)

__version__ = "0.0.2"


class IssueReporter(ast.NodeVisitor):
    def __init__(
        self,
        filename=None,
        allowed_settings=None,
        enable_project_checks=True,
        enable_global_checks=False,
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
            TypeMismatchSettingsIssueFinder(
                filename,
                allowed_settings=allowed_settings,
                exclude_settings=missing_package_settings,
            ),
            InvalidValueSettingsIssueFinder(
                filename,
                allowed_settings=allowed_settings,
                exclude_settings=missing_package_settings,
            ),
            BaseSettingNameIssueFinder(filename),
            UnnecessaryGetIssueFinder(filename),
            IgnoredGetDefaultIssueFinder(filename),
            DuplicateSettingsIssueFinder(filename),
        )
        global_finders = []
        if enable_global_checks:
            global_finders = [
                MissingUserAgentIssueFinder(filename),
                RobotsTxtObeyIssueFinder(filename),
                ThrottlingConfigIssueFinder(filename),
            ]
        project_finders = []
        if enable_project_checks:
            project_finders = [
                RequirementsTxtIssueFinder(filename),
                NonFrozenDependenciesIssueFinder(filename),
                AncientScrapyVersionIssueFinder(filename),
                InsecureScrapyVersionIssueFinder(filename),
                ObsoletePackagesIssueFinder(filename),
            ]
        shared_finders = [*setting_finders, *global_finders, *project_finders]
        node_specific_finders = {
            "Assign": [
                UnreachableDomainIssueFinder(),
                UrlInAllowedDomainsIssueFinder(),
                OldSelectorIssueFinder(),
            ],
            "Call": [UrlJoinIssueFinder()],
        }
        self.finders = {}
        for node_type in [
            "Assign",
            "Call",
            "Subscript",
            "ClassDef",
            "Delete",
            "Module",
        ]:
            specific_finders = node_specific_finders.get(node_type, [])
            self.finders[node_type] = specific_finders + shared_finders

    def find_issues_visitor(self, visitor, node):
        """Find issues for the provided visitor"""
        for finder in self.finders[visitor]:
            issues = finder.find_issues(node)
            if issues:
                self.issues.extend(list(issues))
        self.generic_visit(node)

    def __getattr__(self, name):
        if name.startswith("visit_") and name[6:] in self.finders:
            node_type = name[6:]
            return lambda node: self.find_issues_visitor(node_type, node)
        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}'"
        )


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

    def __init__(
        self, tree, filename, enable_project_checks=True, enable_global_checks=False
    ):
        self.tree = tree
        self.filename = filename
        self.enable_project_checks = enable_project_checks
        self.enable_global_checks = enable_global_checks

    def run(self):
        reporter = IssueReporter(
            self.filename,
            allowed_settings=self.allowed_settings,
            enable_project_checks=self.enable_project_checks,
            enable_global_checks=self.enable_global_checks,
        )
        reporter.visit(self.tree)
        for line, col, msg in reporter.issues:
            yield (line, col, msg, Plugin)
