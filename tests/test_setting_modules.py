"""Test the checking of setting modules as configured in scrapy.cfg."""

from __future__ import annotations

from itertools import combinations

from tests.helpers import check_project

from . import NO_ISSUE, File, Issue, cases


def default_issues(path: str, exclude: int | set[int] | None = None) -> list[Issue]:
    exclude = {exclude} if isinstance(exclude, int) else exclude or set()
    return [
        Issue(
            message=message,
            path=path,
        )
        for message in (
            "SCP19 no USER_AGENT",
            "SCP20 ROBOTSTXT_OBEY not enabled",
            "SCP21 incomplete throttling config",
        )
        if not any(message.startswith(f"SCP{code} ") for code in exclude)
    ]


CASES = [
    # Only modules from scrapy.cfg are checked.
    (
        [
            File("[settings]\na=b", path="scrapy.cfg"),
            File("", path="b.py"),
        ],
        default_issues("b.py"),
    ),
    # settings.py is not assumed to be a settings module.
    (
        [
            File("", path="scrapy.cfg"),
            File("", path="settings.py"),
        ],
        NO_ISSUE,
    ),
    # Multiple settings modules are supported.
    (
        [
            File("[settings]\na=b\nc=d", path="scrapy.cfg"),
            File("", path="b.py"),
            File("", path="d.py"),
        ],
        [
            *default_issues("b.py"),
            *default_issues("d.py"),
        ],
    ),
    # module/__init__.py is supported
    (
        [
            File("[settings]\na=b", path="scrapy.cfg"),
            File("", path="b/__init__.py"),
        ],
        default_issues("b/__init__.py"),
    ),
    # If both module.py and module/__init__.py exist, only the latter is
    # checked
    (
        [
            File("[settings]\na=b", path="scrapy.cfg"),
            File("", path="b.py"),
            File("", path="b/__init__.py"),
        ],
        default_issues("b/__init__.py"),
    ),
    # Settings
    *(
        (
            [
                File("[settings]\na=a", path="scrapy.cfg"),
                File(code, path=path),
            ],
            issues,
        )
        for path in ["a.py"]
        for code, issues in (
            # No issues
            (
                'USER_AGENT = "Jane Doe (+https://jane.doe.example)"\n'
                "ROBOTSTXT_OBEY = True\n"
                "AUTOTHROTTLE_ENABLED = True",
                NO_ISSUE,
            ),
            (
                'USER_AGENT = "Jane Doe (+https://jane.doe.example)"\n'
                "ROBOTSTXT_OBEY = True\n"
                "CONCURRENT_REQUESTS = 1\n"
                "CONCURRENT_REQUESTS_PER_DOMAIN = 1\n"
                "DOWNLOAD_DELAY = 5",
                NO_ISSUE,
            ),
            # SCP19 no USER_AGENT
            (
                "USER_AGENT = 'Jane Doe (+https://jane.doe.example)'",
                default_issues(path, exclude=19),
            ),
            (
                "if a:\n"
                "    USER_AGENT = 'Jane Doe (+https://jane.doe.example)'\n"
                "else:\n"
                "    USER_AGENT = 'John Doe (+https://john.doe.example)'",
                default_issues(path, exclude=19),
            ),
            # SCP20 ROBOTSTXT_OBEY not enabled
            (
                "ROBOTSTXT_OBEY = False",
                (
                    Issue("SCP19 no USER_AGENT", path=path),
                    Issue("SCP20 ROBOTSTXT_OBEY not enabled", column=17, path=path),
                    Issue("SCP21 incomplete throttling config", path=path),
                ),
            ),
            ("ROBOTSTXT_OBEY = True", default_issues(path, exclude=20)),
            (
                "if a:\n    ROBOTSTXT_OBEY = True\nelse:\n    ROBOTSTXT_OBEY = False",
                default_issues(path, exclude=20),
            ),
            # SCP21 incomplete throttling config
            ("AUTOTHROTTLE_ENABLED = False", default_issues(path)),
            *(
                # Combinations of CONCURRENT_REQUESTS,
                # CONCURRENT_REQUESTS_PER_DOMAIN and DOWNLOAD_DELAY that do not
                # include all three
                (
                    "\n".join(f"{setting} = 1" for setting in settings),
                    default_issues(path),
                )
                for settings in [
                    settings
                    for r in [1, 2]
                    for settings in combinations(
                        [
                            "CONCURRENT_REQUESTS",
                            "CONCURRENT_REQUESTS_PER_DOMAIN",
                            "DOWNLOAD_DELAY",
                        ],
                        r,
                    )
                ]
            ),
            ("AUTOTHROTTLE_ENABLED = True", default_issues(path, exclude=21)),
            (
                "if a:\n"
                "    AUTOTHROTTLE_ENABLED = False\n"
                "else:\n"
                "    AUTOTHROTTLE_ENABLED = True",
                default_issues(path, exclude=21),
            ),
            (
                "CONCURRENT_REQUESTS = 1\nCONCURRENT_REQUESTS_PER_DOMAIN = 1\nDOWNLOAD_DELAY = 1",
                default_issues(path, exclude=21),
            ),
            (
                "CONCURRENT_REQUESTS = 1\nCONCURRENT_REQUESTS_PER_DOMAIN = 1\nif a:\n    DOWNLOAD_DELAY = 1\nelse:\n    DOWNLOAD_DELAY = 0",
                default_issues(path, exclude=21),
            ),
            # SCP23 redefined setting
            (
                'BOT_NAME = "a"',
                default_issues(path),
            ),
            (
                'BOT_NAME = "a"\nBOT_NAME = "a"',
                (
                    Issue(
                        "SCP23 redefined setting: seen first at line 1",
                        line=2,
                        path=path,
                    ),
                    *default_issues(path),
                ),
            ),
            (
                'BOT_NAME = "a"\nBOT_NAME = "b"',
                (
                    Issue(
                        "SCP23 redefined setting: seen first at line 1",
                        line=2,
                        path=path,
                    ),
                    *default_issues(path),
                ),
            ),
            (
                'if a:\n    BOT_NAME = "a"\nelse:\n    BOT_NAME = "b"',
                default_issues(path),
            ),
        )
    ),
    # TODO: Use a shared test case constant for value-based checks, so that
    # they are checked both for settings modules and for regular Python files.
    # TODO: SCP07
    # TODO: SCP08
    # TODO: SCP09
    # TODO: SCP10
    # TODO: SCP15
    # TODO: SCP18
    # TODO: SCP22
    # TODO: SCP24
    # TODO: SCP27
]


@cases(CASES)
def test(input: File | list[File], expected: Issue | list[Issue] | None):
    check_project(input, expected)
