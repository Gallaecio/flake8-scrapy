from __future__ import annotations

import ast
from argparse import Namespace
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from flake8_scrapy import Plugin

pytest.register_assert_rewrite("tests.helpers")


def load_sample_file(filename):
    return (Path(__file__).parent / "samples" / filename).read_text()


def run_checker(
    code,
    filename=None,
    allowed_settings=None,
    enable_project_checks=False,
    requirements=None,
):
    tree = ast.parse(code)
    if allowed_settings is not None:
        options = Namespace()
        options.allow_scrapy_settings = ",".join(allowed_settings)
        Plugin.parse_options(options)
    else:
        Plugin.allowed_settings = []
    temp_dir = None
    if requirements is not None:
        if filename is None:
            filename = "foo.py"
        temp_dir = TemporaryDirectory()
        requirements_file = Path(temp_dir.name) / "requirements.txt"
        requirements_file.write_text(requirements)
        file = Path(temp_dir.name) / filename
        file.write_text(code)
        filename = str(file)
    checker = Plugin(
        tree,
        filename,
        enable_project_checks=enable_project_checks,
    )
    result = list(checker.run())
    if temp_dir is not None:
        temp_dir.cleanup()
    return result


@dataclass
class Input:
    code: str
    file_path: str | None = None
    requirements: str | None = None


@dataclass
class Issue:
    message: str
    line: int = 1
    column: int = 0


NO_ISSUE = None
