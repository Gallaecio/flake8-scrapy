from __future__ import annotations

from dataclasses import dataclass

import pytest
from packaging.version import Version

from flake8_scrapy._finders.settings import SCRAPY_VERSION

from . import run_checker


@dataclass
class Input:
    code: str
    filename: str | None = None


@dataclass
class Issue:
    message: str
    line: int = 1
    column: int = 0


NO_ISSUE = None
ISSUE_COLUMN = 9

LOG_UNSERIALIZABLE_REQUESTS_ISSUE = (
    Issue(
        "SCP10: removed Scrapy setting: LOG_UNSERIALIZABLE_REQUESTS (removed "
        "in Scrapy 2.1.0)",
        column=ISSUE_COLUMN,
    )
    if Version("2.1.0") <= SCRAPY_VERSION
    else Issue(
        "SCP08: deprecated Scrapy setting: LOG_UNSERIALIZABLE_REQUESTS (deprecated in Scrapy 2.0.1 or earlier). Use "
        "SCHEDULER_DEBUG instead.",
        column=ISSUE_COLUMN,
    )
)
REQUEST_FINGERPRINTER_IMPLEMENTATION_ISSUE = (
    Issue(
        "SCP08: deprecated Scrapy setting: "
        "REQUEST_FINGERPRINTER_IMPLEMENTATION (deprecated in Scrapy 2.12.0). See "
        "https://flake8-scrapy.readthedocs.io/en/latest/rules/scp08.html#request_fingerprinter_implementation",
        column=ISSUE_COLUMN,
    )
    if Version("2.12.0") <= SCRAPY_VERSION
    else NO_ISSUE
    if Version("2.7.0") <= SCRAPY_VERSION
    else Issue(
        "SCP09: future Scrapy setting: REQUEST_FINGERPRINTER_IMPLEMENTATION "
        "(added in Scrapy 2.7.0)",
        column=ISSUE_COLUMN,
    )
)


@pytest.mark.parametrize(
    ("input", "expected"),
    [
        # Settings are detected
        *(
            (
                case["input"],
                Issue(
                    "SCP07: unknown Scrapy setting: FOO",
                    line=case.get("line", 1),  # type: ignore[arg-type]
                    column=case.get("column", 0),  # type: ignore[arg-type]
                ),
            )
            for setting, value in [("FOO", "bar")]
            for case in (
                {"input": Input(f"{setting} = {value!r}", filename="settings.py")},
                {
                    "input": Input(f'crawler.settings["{setting}"] = {value!r}'),
                    "column": 17,
                },
                {
                    "input": Input(f'self.crawler.settings["{setting}"] = {value!r}'),
                    "column": 22,
                },
                {
                    "input": Input(f'self.crawler.settings.get("{setting}")'),
                    "column": 26,
                },
                {
                    "input": Input(f'self.settings["{setting}"] = {value!r}'),
                    "column": 14,
                },
                {"input": Input(f'settings["{setting}"] = {value!r}'), "column": 9},
                {"input": Input(f'del settings["{setting}"]'), "column": 13},
                {"input": Input(f'settings.get("{setting}")'), "column": 13},
                {"input": Input(f'settings.get(name="{setting}")'), "column": 18},
                {
                    "input": Input(f'settings.update({{"{setting}": {value!r}}})'),
                    "column": 17,
                },
                {
                    "input": Input(
                        f'settings.update(values={{"{setting}": {value!r}}})'
                    ),
                    "column": 24,
                },
                {
                    "input": Input(f"settings.update(dict({setting}={value!r}))"),
                    "column": 21,
                },
                {
                    "input": Input(
                        f"settings.update(values=dict({setting}={value!r}))"
                    ),
                    "column": 28,
                },
                {"input": Input(f'Settings({{"{setting}": {value!r}}})'), "column": 10},
                {
                    "input": Input(f'BaseSettings(values={{"{setting}": {value!r}}})'),
                    "column": 21,
                },
                {"input": Input(f"Settings(dict({setting}={value!r}))"), "column": 14},
                {
                    "input": Input(f"BaseSettings(values=dict({setting}={value!r}))"),
                    "column": 25,
                },
                {
                    "input": Input(
                        f"from scrapy.settings import overridden_settings\n"
                        f"\n"
                        f'settings = overridden_settings({{"{setting}": {value!r}}})\n'
                    ),
                    "line": 3,
                    "column": 32,
                },
                {
                    "input": Input(
                        f"from scrapy import settings\n"
                        f"\n"
                        f'_ = settings.overridden_settings({{"{setting}": {value!r}}})\n'
                    ),
                    "line": 3,
                    "column": 34,
                },
                {
                    "input": Input(
                        f"import scrapy\n"
                        f"\n"
                        f'settings = scrapy.settings.overridden_settings({{"{setting}": {value!r}}})\n'
                    ),
                    "line": 3,
                    "column": 48,
                },
                {
                    "input": Input(
                        f'overridden_settings(settings={{"{setting}": {value!r}}})\n'
                    ),
                    "column": 30,
                },
                {
                    "input": Input(
                        f"import scrapy\n"
                        f"\n"
                        f"class MySpider(scrapy.Spider):\n"
                        f'    name = "myspider"\n'
                        f"    custom_settings = {{\n"
                        f'        "{setting}": {value!r},\n'
                        f"    }}\n"
                    ),
                    "line": 6,
                    "column": 8,
                },
            )
        ),
        # Non-settings are ignored
        *(
            (input, NO_ISSUE)
            for input in (
                # Outside settings.py, module-level uppercase variables are not
                # considered settings.
                Input('FOO = "BAR"'),
                # In settings.py, variables that are _-prefixed, lowercase or
                # shorter than 3 characters are not considered settings.
                Input('_FOO = "BAR"', filename="settings.py"),
                Input('foo = "BAR"', filename="settings.py"),
                Input('FO = "BAR"', filename="settings.py"),
                # Dict class variables other than custom_settings are
                # not considered settings.
                Input('class MyClass:\n    foo = {\n        "FOO": "bar",\n    }\n'),
                # Non-str values are not considered settings
                Input("settings[0]"),
                Input('settings.update({0: "bar"})'),
                # Dicts defined in variables are not considered settings
                Input('new_settings = {"FOO": "bar"}\nsettings.update(new_settings)'),
                # dict() is ignored if **kwargs is used
                Input('kwargs = {"FOO": "bar"}\nsettings.update(dict(**kwargs))'),
                # Unknown method of settings objects are ignored
                Input('settings.foo("FOO")'),
                # Test deletion with non-settings objects should be ignored
                Input('del crawler.non_settings["FOO"]'),
                Input('del self.crawler.non_settings["FOO"]'),
                Input("del settings"),
                # Test keyword args that don't match expected param name are
                # ignored
                Input('settings.get(foo="FOO")'),
                Input('settings.update(foo={"FOO": "bar"})'),
                # Non-string constants should be ignored
                Input("settings.get(123)"),
                Input("settings.get(name=123)"),
                # Corner cases that should be ignored
                Input('foo["settings"]["FOO"] = "bar"'),
                Input('foo["overridden_settings"]({"FOO": "bar"})'),
                Input('crawler.non_settings["FOO"] = "bar"'),
                # Test deletion operations with non-strings should be ignored
                Input("del settings[123]"),
                Input("del settings[variable]"),
                # Callables with a bad keyword arg are ignored
                Input('BaseSettings(foo={"FOO": True})'),
                Input('overridden_settings(foo={"FOO": "test"})'),
            )
        ),
        # Different setting issues trigger different errors
        *(
            (Input(f'settings["{setting}"] = {value!r}'), issue)
            for setting, value, issue in [
                ("BOT_NAME", None, NO_ISSUE),
                (
                    "REQUEST_FINGERPRINTER_IMPLEMENTATION",
                    "2.6",
                    REQUEST_FINGERPRINTER_IMPLEMENTATION_ISSUE,
                ),
                (
                    "LOG_UNSERIALIZABLE_REQUESTS",
                    True,
                    LOG_UNSERIALIZABLE_REQUESTS_ISSUE,
                ),
            ]
        ),
        # For unknown settings, suggestions may be provided.
        (
            # 1 hardcoded
            Input("DELAY = 5", filename="settings.py"),
            Issue("SCP07: unknown Scrapy setting: DELAY. Did you mean DOWNLOAD_DELAY?"),
        ),
        (
            # 1 automatic
            Input("ADD_ONS = {}", filename="settings.py"),
            Issue("SCP07: unknown Scrapy setting: ADD_ONS. Did you mean ADDONS?"),
        ),
        (
            # 2+ hardcoded
            Input("CONCURRENCY = 1", filename="settings.py"),
            Issue(
                "SCP07: unknown Scrapy setting: CONCURRENCY. Did you mean one "
                "of: CONCURRENT_REQUESTS, CONCURRENT_REQUESTS_PER_DOMAIN?"
            ),
        ),
        (
            # 2+ automatic
            Input("CONCURRENT_REQUESTS_PER_SLOT = 1", filename="settings.py"),
            Issue(
                "SCP07: unknown Scrapy setting: CONCURRENT_REQUESTS_PER_SLOT. "
                "Did you mean one of: CONCURRENT_REQUESTS_PER_IP, "
                "CONCURRENT_REQUESTS_PER_DOMAIN, CONCURRENT_REQUESTS?"
            ),
        ),
    ],
)
def test_main(input, expected):
    issues = run_checker(input.code, input.filename)
    if expected is None:
        assert len(issues) == 0
        return
    assert len(issues) == 1
    issue = issues[0]
    assert issue[2] == expected.message
    assert issue[0] == expected.line
    assert issue[1] == expected.column
