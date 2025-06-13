from __future__ import annotations

import ast
import sys
from configparser import ConfigParser
from contextlib import contextmanager
from importlib.util import find_spec
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from flake8_scrapy._finders.settings_module import SettingsModuleIssueFinder
from flake8_scrapy.config import Config

from ._finders.domains import (
    UnreachableDomainIssueFinder,
    UrlInAllowedDomainsIssueFinder,
)
from ._finders.oldstyle import OldSelectorIssueFinder, UrlJoinIssueFinder
from ._finders.settings import (
    BaseSettingNameIssueFinder,
    DeprecatedSettingsIssueFinder,
    FutureSettingsIssueFinder,
    IgnoredGetDefaultIssueFinder,
    ImportPathStringIssueFinder,
    InvalidValueSettingsIssueFinder,
    MissingPackageSettingsIssueFinder,
    RemovedSettingsIssueFinder,
    TypeMismatchSettingsIssueFinder,
    UnknownSettingsIssueFinder,
    UnnecessaryGetIssueFinder,
)
from .requirements import check_requirements

__version__ = "0.0.2"

if TYPE_CHECKING:
    from collections.abc import Generator

    from flake8_scrapy._finders.messaging import Issue


@contextmanager
def extend_sys_path(path):
    original_sys_path = sys.path.copy()
    sys.path.insert(0, path)
    try:
        yield
    finally:
        sys.path = original_sys_path


class ScrapyStyleIssueFinder(ast.NodeVisitor):
    def __init__(
        self,
        filename=None,
        allowed_settings=None,
        enable_project_checks=True,
    ):
        super().__init__()
        self.issues = []
        # MissingPackageSettingsIssueFinder must be first to have priority
        missing_package_finder = MissingPackageSettingsIssueFinder(
            filename, allowed_settings=allowed_settings
        )

        # Get settings that are missing packages to exclude from other checks
        missing_package_settings = missing_package_finder.missing_package_settings

        setting_finders = [
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
            ImportPathStringIssueFinder(filename),
            UnnecessaryGetIssueFinder(filename),
            IgnoredGetDefaultIssueFinder(filename),
        ]
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
            self.finders[node_type] = specific_finders + setting_finders

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
    user_known_settings: ClassVar[set[str]] = set()

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
        if not options.known_scrapy_settings:
            return
        cls.user_known_settings = {
            setting.strip()
            for setting in options.known_scrapy_settings.split(",")
            if setting.strip()
        }

    def __init__(
        self,
        tree: ast.AST | None,
        filename: str,
        lines: list[str],
        enable_project_checks=True,
    ):
        self.tree = tree
        self.filename = filename
        self.lines = lines
        self.enable_project_checks = enable_project_checks
        self.config = Config(
            file_path=filename,
            user_known_settings=self.user_known_settings,
        )

    def run(self):
        for issue in self.run_checks():
            yield (*issue, Plugin)

    def run_checks(self):
        if self.is_settings_module():
            yield from self.check_settings_module()
        elif self.tree:
            yield from self.check_code()
        elif Path(self.filename).name == "requirements.txt":
            yield from self.check_requirements()

    def is_settings_module(self) -> bool:
        if not self.filename:
            return False
        root = self.get_project_root()
        if not root:
            return False
        config_file = root / "scrapy.cfg"
        config = ConfigParser()
        config.read(config_file)
        if "settings" not in config:
            return False
        file_path = Path(self.filename).resolve()
        with extend_sys_path(str(root.resolve())):
            for module in config["settings"].values():
                spec = find_spec(module)
                if not spec or not spec.origin:
                    continue
                module_path = Path(spec.origin).resolve()
                if module_path == file_path:
                    return True
        return False

    def get_project_root(self):
        if not self.filename:
            return None
        path = Path(self.filename).resolve()
        for parent in [path, *list(path.parents)]:
            if (parent / "scrapy.cfg").exists():
                return parent
        return None

    def check_settings_module(self) -> Generator[Issue, None, None]:
        finder = SettingsModuleIssueFinder(self.config)
        assert self.tree is not None
        finder.visit(self.tree)
        yield from finder.issues

    def check_code(self) -> Generator[Issue, None, None]:
        finder = ScrapyStyleIssueFinder(
            self.filename,
            allowed_settings=self.user_known_settings,
            enable_project_checks=self.enable_project_checks,
        )
        assert self.tree is not None
        finder.visit(self.tree)
        yield from finder.issues

    def check_requirements(self) -> Generator[Issue, None, None]:
        yield from check_requirements(self.filename, self.lines)
