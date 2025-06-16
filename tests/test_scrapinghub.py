from . import NO_ISSUE, File, Issue, cases
from .helpers import check_project


def issue(message, path="scrapinghub.yml", **kwargs):
    return Issue(message, path=path, **kwargs)


LATEST_KNOWN_STACK = "scrapy:2.12-20241202"


CASES = [
    # Config content
    *(
        (
            (File(config, "scrapinghub.yml"), File("", "scrapy.cfg")),
            issues,
        )
        for config, issues in (
            # SCP18 no root stack
            *(
                (config, issue("SCP18 no root stack"))
                for config in (
                    "requirements:\n  file: requirements.txt",
                    f"projects:\n  default:\n    id: 12345\n    stack: {LATEST_KNOWN_STACK}",
                )
            ),
            *(
                (config, NO_ISSUE)
                for config in (
                    f"requirements:\n  file: requirements.txt\nstack: {LATEST_KNOWN_STACK}",
                    "invalid: yaml: content:",
                    "- not a dict",
                    "project: 12345\nstack:",
                )
            ),
        )
    ),
    # Only a root scrapinghub.yml file is checked
    *(
        (
            (File("project: 12345", path), File("", "scrapy.cfg")),
            issues,
        )
        for path, issues in (
            ("scrapinghub.yml", issue("SCP18 no root stack")),
            *(
                (path, NO_ISSUE)
                for path in (
                    "not-scrapinghub.yml",
                    "subdir/scrapinghub.yml",
                )
            ),
        )
    ),
]


@cases(CASES)
def test(input, expected):
    check_project(input, expected)
