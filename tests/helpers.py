# Helper functions that require pytest assert rewriting
# https://docs.pytest.org/en/latest/how-to/writing_plugins.html#assertion-rewriting

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from . import File, Issue, cwd, run_checker


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
    relative_file_path = input.path or "a.py"
    if expected:
        if isinstance(expected, Issue):
            expected = [expected]
        for issue in expected:
            issue.path = issue.path or relative_file_path

    if (
        relative_file_path
        and Path(relative_file_path).name == "settings.py"
        and fix_global_settings
    ):
        # Add settings that, if missing from settings.py, trigger issues.
        code += "\n"
        for name, value in GLOBAL_SETTINGS.items():
            if not re.search(f"^{name}\\b", code):
                code += f"{name} = {value!r}\n"

    files = [
        File(code, path=relative_file_path),
        File("", path="scrapy.cfg"),
    ]
    files.append(File(input.requirements or "", path="requirements.txt"))
    check_project(files, expected)


def check_project(input: File | list[File], expected: Issue | list[Issue] | None):
    """Build a project with a set of files and test it."""
    if isinstance(input, File):
        input = [input]
    if isinstance(expected, Issue):
        expected = [expected]
    elif expected is None:
        expected = []
    with TemporaryDirectory() as dir:
        for file in input:
            file.path = file.path or "a.py"
            file_path = Path(dir) / file.path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(file.text)
        with cwd(dir):
            issues = []
            for file in input:
                if not (
                    file.path.endswith(".py")
                    or Path(file.path).name == "requirements.txt"
                ):
                    continue
                file_issues = run_checker(
                    file.text, file.path, enable_project_checks=True
                )
                issues.extend(
                    [Issue.from_tuple(issue, path=file.path) for issue in file_issues]
                )
            assert tuple(issues) == tuple(expected)
