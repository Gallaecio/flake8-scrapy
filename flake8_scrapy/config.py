from __future__ import annotations

from difflib import get_close_matches
from pathlib import Path
from typing import TYPE_CHECKING

from packaging.utils import canonicalize_name

from flake8_scrapy.finders.data import (
    HARDCODED_SUGGESTIONS,
    MAX_SUGGESTIONS,
    MIN_SUGGESTION_SCORE,
    SETTINGS,
)
from flake8_scrapy.finders.versions import (
    build_package_versions_dict,
    is_version_greater_than,
    is_version_less_than_or_equal,
)

if TYPE_CHECKING:
    from packaging.version import Version


class Config:
    def __init__(self, *, file_path: str, user_known_settings: set[str] | None = None):
        user_known_settings = user_known_settings or set()
        self.known_settings = set(SETTINGS) | user_known_settings
        self.init_project_root(file_path)
        self.package_versions = build_package_versions_dict(self.project_root)
        self.init_deprecated_settings()

    def get_package_version(self, package_name) -> Version | None:
        return self.package_versions.get(canonicalize_name(package_name), None)

    def init_project_root(self, file_path):
        self.project_root = None
        if not file_path:
            return
        path = Path(file_path).resolve()
        for parent in [path, *list(path.parents)]:
            if (parent / "scrapy.cfg").exists():
                self.project_root = parent
                return

    def init_deprecated_settings(self):
        deprecated = set()
        for name, info in SETTINGS.items():
            package_version = self.get_package_version(info.package)
            if package_version is None:
                continue
            if info.removed_version and is_version_less_than_or_equal(
                info.removed_version, package_version
            ):
                continue
            if info.added_version and is_version_greater_than(
                info.added_version, package_version
            ):
                continue
            if info.deprecated_version and is_version_less_than_or_equal(
                info.deprecated_version, package_version
            ):
                deprecated.add(name)
        self.deprecated_settings = deprecated

    def is_known_setting(self, name: str) -> bool:
        return name in self.known_settings

    def get_setting_suggestions(self, name: str) -> list[str]:
        normalized_name = name.upper()
        hardcoded = HARDCODED_SUGGESTIONS.get(normalized_name)
        if hardcoded:
            return hardcoded[:MAX_SUGGESTIONS]
        return get_close_matches(
            normalized_name,
            self.known_settings,
            n=MAX_SUGGESTIONS,
            cutoff=MIN_SUGGESTION_SCORE,
        )
