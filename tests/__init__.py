from __future__ import annotations

import ast
import re
from argparse import Namespace
from contextlib import contextmanager
from dataclasses import dataclass
from os import chdir
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from flake8_scrapy import Plugin

pytest.register_assert_rewrite("tests.helpers")


def load_sample_file(filename):
    return (Path(__file__).parent / "samples" / filename).read_text()


def cases(
    test_cases: list[tuple[File | list[File], Issue | list[Issue] | None]],
) -> callable:
    def decorator(func):
        return pytest.mark.parametrize(
            ("input", "expected"),
            test_cases,
            ids=range(len(test_cases)),
        )(func)

    return decorator


@contextmanager
def cwd(dir):
    old_dir = Path.cwd()
    chdir(dir)
    try:
        yield
    finally:
        chdir(old_dir)


def run_checker(
    code,
    filename=None,
    allowed_settings=None,
    enable_project_checks=False,
    requirements=None,
):
    # TODO: Remove the need for enable_project_checks
    tree = ast.parse(code) if filename is None or filename.endswith(".py") else None
    if allowed_settings is not None:
        options = Namespace()
        options.allow_scrapy_settings = ",".join(allowed_settings)
        Plugin.parse_options(options)
    else:
        Plugin.allowed_settings = []
    temp_dir = None
    if requirements is not None:
        if filename is None:
            filename = "a.py"
        temp_dir = TemporaryDirectory()
        requirements_file = Path(temp_dir.name) / "requirements.txt"
        requirements_file.write_text(requirements)
        file = Path(temp_dir.name) / filename
        file.write_text(code)
        filename = str(file)
    if filename is None:
        filename = "a.py"
    checker = Plugin(
        tree,
        filename,
        lines=code.splitlines(keepends=True),
        enable_project_checks=enable_project_checks,
    )
    result = list(checker.run())
    if temp_dir is not None:
        temp_dir.cleanup()
    return result


class RegExpMatcher:
    def __init__(self, pattern: str = ""):
        self.pattern = re.compile(pattern)

    def __eq__(self, other: str) -> bool:
        return self.pattern.search(other) is not None

    def __repr__(self):
        return f"RegexMatcher({self.pattern.pattern!r})"


@dataclass
class File:
    text: str
    path: str | None = None


@dataclass
class Input:
    code: str
    path: str | None = None
    requirements: str | None = None


@dataclass
class Issue:
    message: str | RegExpMatcher
    line: int = 1
    column: int = 0
    path: str | None = None

    @classmethod
    def from_tuple(cls, issue: tuple[int, int, str], path: str | None = None) -> Issue:
        return cls(
            message=issue[2],
            line=issue[0],
            column=issue[1],
            path=path,
        )


NO_ISSUE = None
SOME_ISSUE = Issue(RegExpMatcher(), path=RegExpMatcher())
