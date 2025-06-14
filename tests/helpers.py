# Helper functions that require pytest assert rewriting
# https://docs.pytest.org/en/latest/how-to/writing_plugins.html#assertion-rewriting

from __future__ import annotations

from typing import TYPE_CHECKING

from . import File, Issue, run_checker

if TYPE_CHECKING:
    from collections.abc import Sequence


def check_project(
    input: File | Sequence[File], expected: Issue | Sequence[Issue] | None
):
    if isinstance(input, File):
        input = [input]
    if isinstance(expected, Issue):
        expected = [expected]
    elif expected is None:
        expected = []
    issues = []
    for file in input:
        issue_tuples = run_checker(file.text)
        issues.extend(
            [Issue.from_tuple(issue, path=file.path) for issue in issue_tuples]
        )
    assert tuple(expected) == tuple(issues)
