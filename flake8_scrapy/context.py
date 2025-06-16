from __future__ import annotations

from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ast import AST
    from collections.abc import Sequence


@dataclass
class Flake8File:
    tree: AST | None
    path: Path

    @classmethod
    def from_params(cls, tree: AST | None, file_path: str):
        return cls(tree, Path(file_path).resolve())


@dataclass
class Project:
    root: Path | None
    setting_module_import_paths: Sequence[str]
    requirements_file_path: Path | None = None

    @classmethod
    def from_file(cls, file: Flake8File, requirements_file_path: str):
        root = cls.root_from_file(file)
        return cls(
            root,
            cls.setting_module_import_paths_from_root(root),
            cls.find_requirements_file_path(requirements_file_path, root),
        )

    @staticmethod
    def root_from_file(file: Flake8File) -> Path | None:
        for parent in [file.path, *list(file.path.parents)]:
            if (parent / "scrapy.cfg").exists():
                return parent
        return None

    @staticmethod
    def setting_module_import_paths_from_root(root: Path | None) -> Sequence[str]:
        if not root:
            return ()
        config_file = root / "scrapy.cfg"
        config = ConfigParser()
        config.read(config_file)
        if "settings" not in config:
            return ()
        return tuple(config["settings"].values())

    @staticmethod
    def find_requirements_file_path(
        requirements_file_path: str, root: Path | None
    ) -> Path | None:
        if requirements_file_path:
            return Path(requirements_file_path).resolve()
        if not root:
            return None
        requirements_file = root / "requirements.txt"
        if requirements_file.exists():
            return requirements_file.resolve()
        return None


@dataclass
class Context:
    file: Flake8File
    project: Project

    @classmethod
    def from_flake8_params(
        cls, tree: AST | None, file_path: str, requirements_file_path: str = ""
    ):
        file = Flake8File.from_params(tree, file_path)
        return cls(
            file,
            Project.from_file(file, requirements_file_path),
        )
