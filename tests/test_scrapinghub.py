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
            *(
                (config, NO_ISSUE)
                for config in (
                    "\n".join(
                        [
                            "requirements:",
                            "  file: requirements.txt",
                            f"stack: {LATEST_KNOWN_STACK}",
                        ]
                    ),
                    "invalid: yaml: content:",
                    "- not a dict",
                    "image: custom:latest",
                    "\n".join(
                        [
                            "image: custom:latest",
                            "projects:",
                            "  default:",
                            "    stack: scrapy:2.12",
                        ]
                    ),
                )
            ),
            # SCP18 no root stack
            *(
                (config, issue("SCP18 no root stack"))
                for config in (
                    "\n".join(["requirements:", "  file: requirements.txt"]),
                )
            ),
            # SCP19 non-root stack
            *(
                (config, issue("SCP19 non-root stack"))
                for config in (
                    "\n".join(
                        [
                            f"stack: {LATEST_KNOWN_STACK}",
                            "projects:",
                            "  default:",
                            f"    stack: {LATEST_KNOWN_STACK}",
                        ]
                    ),
                )
            ),
            # SCP20 stack not frozen
            *(
                (config, issue("SCP20 stack not frozen"))
                for config in (
                    "stack: scrapy:2.12",
                    "stack: scrapy:latest",
                    "stack: scrapy:2.12-rc1",
                    "\n".join(["project: 12345", "stack:"]),
                )
            ),
            # Multiple issues
            (
                "\n".join(
                    [
                        "projects:",
                        "  default:",
                        "    id: 12345",
                        "    stack: 2.12",
                    ]
                ),
                (
                    issue("SCP18 no root stack"),
                    issue("SCP19 non-root stack"),
                    issue("SCP20 stack not frozen"),
                ),
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
