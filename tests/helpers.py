# Helper functions that require pytest assert rewriting
# https://docs.pytest.org/en/latest/how-to/writing_plugins.html#assertion-rewriting

from __future__ import annotations

from . import File, Issue, run_checker


def check_project(input: File | list[File], expected: Issue | list[Issue] | None):
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
