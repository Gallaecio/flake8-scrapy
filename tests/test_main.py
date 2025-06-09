from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from . import Input, Issue
from .helpers import check_input

if TYPE_CHECKING:
    from . import Input, Issue

# Test cases are kept in separate variables so that they do not show up in
# pytest tracebacks, as they only add noise.
MAIN_TEST_CASES = []
GLOBAL_TEST_CASES = []


@pytest.mark.parametrize(
    ("input", "expected"),
    MAIN_TEST_CASES,
)
def test_main(input: Input, expected: Issue | None):
    """Test arbitrary input code.

    If input.file_path is "settings.py", additional settings may be injected to
    avoid reports of issues that are already covered by test_global_settings.
    """
    check_input(input, expected, fix_global_settings=True)


@pytest.mark.parametrize(
    ("input", "expected"),
    GLOBAL_TEST_CASES,
)
def test_global_settings(input: Input, expected: Issue | None):
    """Test settings.py code as is."""
    check_input(input, expected)
