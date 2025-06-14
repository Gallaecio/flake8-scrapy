# Helper functions that require pytest assert rewriting
# https://docs.pytest.org/en/latest/how-to/writing_plugins.html#assertion-rewriting

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

from . import File, Issue, chdir, run_checker

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
    with TemporaryDirectory() as dir:
        for file in input:
            assert file.path is not None
            file_path = Path(dir) / file.path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(file.text)
        with chdir(dir):
            issues = []
            for file in input:
                assert file.path is not None
                if not file.path.endswith(".py"):
                    continue
                issue_tuples = run_checker(file.text, file.path)
                issues.extend(
                    [Issue.from_tuple(issue, path=file.path) for issue in issue_tuples]
                )
            assert tuple(expected) == tuple(issues)
