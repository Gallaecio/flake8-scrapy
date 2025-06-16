from __future__ import annotations

from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from ast import AST
    from collections.abc import Sequence


@dataclass
class Flake8File:
    tree: AST | None
    path: Path
    lines: Sequence[str] | None = None

    @classmethod
    def from_params(
        cls, tree: AST | None, file_path: str, lines: Sequence[str] | None = None
    ):
        return cls(tree, Path(file_path).resolve(), lines)


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

        # Check scrapinghub.yml for requirements file
        scrapinghub_file = root / "scrapinghub.yml"
        if scrapinghub_file.exists():
            try:
                with scrapinghub_file.open() as f:
                    data = yaml.safe_load(f)
                if (
                    isinstance(data, dict)
                    and "requirements" in data
                    and isinstance(data["requirements"], dict)
                    and "file" in data["requirements"]
                    and isinstance(data["requirements"]["file"], str)
                    and data["requirements"]["file"].strip()
                ):
                    scrapinghub_requirements_file = root / data["requirements"]["file"]
                    if scrapinghub_requirements_file.exists():
                        return scrapinghub_requirements_file.resolve()
            except yaml.YAMLError:
                pass

        # Fall back to requirements.txt
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
        cls,
        tree: AST | None,
        file_path: str,
        lines: Sequence[str] | None = None,
        requirements_file_path: str = "",
    ):
        file = Flake8File.from_params(tree, file_path, lines)
        project = Project.from_file(file, requirements_file_path)
        return cls(file, project)
