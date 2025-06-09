# Helper functions that require pytest assert rewriting
# https://docs.pytest.org/en/latest/how-to/writing_plugins.html#assertion-rewriting

import re
from dataclasses import dataclass
from pathlib import Path

from . import run_checker


@dataclass
class IssueSubset:
    message: str
    line: int
    column: int


GLOBAL_SETTINGS = {
    "USER_AGENT": "jane@doe.example",
    "ROBOTSTXT_OBEY": True,
    "CONCURRENT_REQUESTS": 1,
    "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
    "DOWNLOAD_DELAY": 5,
}


def check_input(input, expected, fix_global_settings=False):
    code = input.code
    file_path = input.file_path

    if file_path and Path(file_path).name == "settings.py" and fix_global_settings:
        # Add settings that, if missing from settings.py, trigger issues.
        code += "\n"
        for name, value in GLOBAL_SETTINGS.items():
            if not re.search(f"^{name}\\b", code):
                code += f"{name} = {value!r}\n"

    issues = run_checker(
        code,
        input.file_path,
        requirements=input.requirements,
    )

    if expected is None:
        assert len(issues) == 0
        return

    if not isinstance(expected, list):
        expected = [expected]
    actual = [IssueSubset(issue[2], issue[0], issue[1]) for issue in issues]
    expected = [IssueSubset(e.message, e.line, e.column) for e in expected]
    assert actual == expected
