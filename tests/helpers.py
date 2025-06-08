# Helper functions that require pytest assert rewriting
# https://docs.pytest.org/en/latest/how-to/writing_plugins.html#assertion-rewriting

from . import run_checker


def check_input(input, expected):
    issues = run_checker(input.code, input.filename, requirements=input.requirements)
    if expected is None:
        assert len(issues) == 0
        return
    assert len(issues) == 1
    issue = issues[0]
    assert issue[2] == expected.message
    assert issue[0] == expected.line
    assert issue[1] == expected.column
