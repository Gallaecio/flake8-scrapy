# Helper functions that require pytest assert rewriting
# https://docs.pytest.org/en/latest/how-to/writing_plugins.html#assertion-rewriting

from dataclasses import dataclass

from . import run_checker


@dataclass
class IssueSubset:
    message: str
    line: int
    column: int


def check_input(input, expected, enable_global_checks=False):
    issues = run_checker(
        input.code,
        input.filename,
        requirements=input.requirements,
        enable_global_checks=enable_global_checks,
    )
    if expected is None:
        assert len(issues) == 0
        return
    if not isinstance(expected, list):
        expected = [expected]
    actual = [IssueSubset(issue[2], issue[0], issue[1]) for issue in issues]
    expected = [IssueSubset(e.message, e.line, e.column) for e in expected]
    assert actual == expected
