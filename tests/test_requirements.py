"""Test requirements.txt file checks."""

from __future__ import annotations

from packaging.version import Version

from flake8_scrapy._finders.data import LATEST_KNOWN_SCRAPY_VERSION

from . import NO_ISSUE, File, Issue, RegExpMatcher, cases
from .helpers import check_project

# A fictitious future Scrapy version for testing purposes.
FUTURE_SCRAPY_VERSION = Version("3.14")


def RequirementsIssue(
    message: str | RegExpMatcher, line: int = 1, column: int = 0
) -> Issue:
    return Issue(message=message, line=line, column=column, path="requirements.txt")


CASES = [
    *(
        (
            File(content, path="requirements.txt"),
            RequirementsIssue(issues)
            if isinstance(issues, (str, RegExpMatcher))
            else issues,
        )
        for content, issues in (
            # Ignored
            ("", NO_ISSUE),
            ("#", NO_ISSUE),
            ("\n", NO_ISSUE),
            ("a==1 #", NO_ISSUE),
            ("-r a", NO_ISSUE),
            ("-e a", NO_ISSUE),
            ("https://a.example/a.zip", NO_ISSUE),
            # Non-frozen and duplicate dependencies
            (
                "a==1\na==1",
                RequirementsIssue(
                    "SCP11 duplicate dependency: first seen on line 1", line=2
                ),
            ),
            (
                "a==1\na==2",
                RequirementsIssue(
                    "SCP11 duplicate dependency: first seen on line 1", line=2
                ),
            ),
            (
                "a==1\nb==2\nb==2",
                RequirementsIssue(
                    "SCP11 duplicate dependency: first seen on line 2", line=3
                ),
            ),
            ("a", "SCP12 non-frozen dependency"),
            ("a>=1", "SCP12 non-frozen dependency"),
            (
                "a\na",
                (
                    RequirementsIssue("SCP12 non-frozen dependency"),
                    RequirementsIssue(
                        "SCP11 duplicate dependency: first seen on line 1", line=2
                    ),
                ),
            ),
            (
                "a>1\na<2",
                (
                    RequirementsIssue("SCP12 non-frozen dependency"),
                    RequirementsIssue(
                        "SCP11 duplicate dependency: first seen on line 1", line=2
                    ),
                ),
            ),
            (
                "a>1\na==2",
                (
                    RequirementsIssue("SCP12 non-frozen dependency"),
                    RequirementsIssue(
                        "SCP11 duplicate dependency: first seen on line 1", line=2
                    ),
                ),
            ),
            (
                "a==1\na<2\na==2",
                (
                    RequirementsIssue(
                        "SCP11 duplicate dependency: first seen on line 1", line=2
                    ),
                    RequirementsIssue(
                        "SCP11 duplicate dependency: first seen on line 1", line=3
                    ),
                ),
            ),
            # Scrapy version
            ("scrapy==1.8.4", "SCP13 ancient Scrapy"),
            ("scrapy==2.0.0", "SCP13 ancient Scrapy"),
            ("scrapy==2.0.1", "SCP14 unsafe Scrapy"),
            ("scrapy==2.11.1", "SCP14 unsafe Scrapy"),
            ("scrapy==2.11.2", NO_ISSUE),
            ("scrapy==2.11.2", NO_ISSUE),
            (f"scrapy=={LATEST_KNOWN_SCRAPY_VERSION}", NO_ISSUE),
            (f"scrapy=={FUTURE_SCRAPY_VERSION}", NO_ISSUE),
            # Unknown package versions
            ("a==1.8.4", NO_ISSUE),
            ("a==2.0.0", NO_ISSUE),
            ("a==2.0.1", NO_ISSUE),
            ("a==2.11.1", NO_ISSUE),
            ("a==2.11.2", NO_ISSUE),
            ("a==2.11.2", NO_ISSUE),
            (f"a=={LATEST_KNOWN_SCRAPY_VERSION}", NO_ISSUE),
            (f"a=={FUTURE_SCRAPY_VERSION}", NO_ISSUE),
            # Obsolete packages
            ("scrapy-crawlera==1.7.0", "SCP16 obsolete package"),
            ("scrapy-splash==0.8.0", "SCP16 obsolete package"),
        )
    ),
    # Non-root requirements.txt files are ignored
    (
        File("a", path="a/requirements.txt"),
        NO_ISSUE,
    ),
]


@cases(CASES)
def test(input: File, expected: Issue | list[Issue] | None):
    files = [input, File("", path="scrapy.cfg")]
    check_project(files, expected)


def test_future_scrapy_version():
    """Test that the future Scrapy version is now the same or lower than the
    latest known version.

    Otherwise, LATEST_KNOWN_SCRAPY_VERSION will need to be updated.
    """
    assert FUTURE_SCRAPY_VERSION > LATEST_KNOWN_SCRAPY_VERSION
