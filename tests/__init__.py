from __future__ import annotations

import ast
from argparse import Namespace
from dataclasses import dataclass
from pathlib import Path

from flake8_scrapy import Plugin


def load_sample_file(filename):
    return (Path(__file__).parent / "samples" / filename).read_text()


def run_checker(
    code, filename=None, allowed_settings=None, enable_project_checks=False
):
    tree = ast.parse(code)
    if allowed_settings is not None:
        options = Namespace()
        options.allow_scrapy_settings = ",".join(allowed_settings)
        Plugin.parse_options(options)
    else:
        Plugin.allowed_settings = []
    checker = Plugin(tree, filename, enable_project_checks=enable_project_checks)
    return list(checker.run())


@dataclass
class Input:
    code: str
    filename: str | None = None


@dataclass
class Issue:
    message: str
    line: int = 1
    column: int = 0


NO_ISSUE = None


def check_input(input, expected):
    issues = run_checker(input.code, input.filename)
    if expected is None:
        assert len(issues) == 0
        return
    assert len(issues) == 1
    issue = issues[0]
    assert issue[2] == expected.message
    assert issue[0] == expected.line
    assert issue[1] == expected.column
