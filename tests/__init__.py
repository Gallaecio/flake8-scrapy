from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pytest

from flake8_scrapy import ScrapyStyleChecker

NO_ISSUE = None

pytest.register_assert_rewrite("tests.helpers")


def cases(
    test_cases: tuple[tuple[File | list[File], Issue | list[Issue] | None], ...],
) -> Callable:
    def decorator(func):
        return pytest.mark.parametrize(
            ("input", "expected"),
            test_cases,
            ids=range(len(test_cases)),
        )(func)

    return decorator


def load_sample_file(filename):
    return (Path(__file__).parent / "samples" / filename).read_text()


def run_checker(code: str) -> list[tuple[int, int, str]]:
    tree = ast.parse(code)
    checker = ScrapyStyleChecker(tree, None)
    return list(checker.run())


class RegExpMatcher:
    def __init__(self, pattern: str = ""):
        self.pattern = re.compile(pattern)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.pattern.search(other) is not None
        raise NotImplementedError

    def __repr__(self):
        return f"RegexMatcher({self.pattern.pattern!r})"


@dataclass
class File:
    text: str
    path: str | None = None


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
