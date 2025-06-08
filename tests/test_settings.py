from __future__ import annotations

import pytest

from flake8_scrapy._finders import (
    LATEST_KNOWN_SCRAPY_VERSION,
    MINIMUM_SUPPORTED_SCRAPY_VERSION,
)

from . import NO_ISSUE, Input, Issue, run_checker
from .helpers import check_input

ISSUE_COLUMN = 9


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
            (
                Input(f'settings["{setting}"] = {value!r}', requirements=requirements),
                issue,
            )
            for setting, value, requirements, issue in [
                ("BOT_NAME", None, None, NO_ISSUE),
                (
                    "REQUEST_FINGERPRINTER_IMPLEMENTATION",
                    "2.6",
                    f"scrapy=={LATEST_KNOWN_SCRAPY_VERSION}",
                    Issue(
                        "SCP08: deprecated Scrapy setting: "
                        "REQUEST_FINGERPRINTER_IMPLEMENTATION (deprecated in Scrapy 2.12.0). See "
                        "https://flake8-scrapy.readthedocs.io/en/latest/rules/scp08.html#request_fingerprinter_implementation",
                        column=ISSUE_COLUMN,
                    ),
                ),
                (
                    "REQUEST_FINGERPRINTER_IMPLEMENTATION",
                    "2.6",
                    "scrapy==2.12.0",
                    Issue(
                        "SCP08: deprecated Scrapy setting: "
                        "REQUEST_FINGERPRINTER_IMPLEMENTATION (deprecated in Scrapy 2.12.0). See "
                        "https://flake8-scrapy.readthedocs.io/en/latest/rules/scp08.html#request_fingerprinter_implementation",
                        column=ISSUE_COLUMN,
                    ),
                ),
                (
                    "REQUEST_FINGERPRINTER_IMPLEMENTATION",
                    "2.6",
                    "scrapy==2.11.2",
                    NO_ISSUE,
                ),
                (
                    "REQUEST_FINGERPRINTER_IMPLEMENTATION",
                    "2.6",
                    "scrapy==2.7.0",
                    NO_ISSUE,
                ),
                (
                    "REQUEST_FINGERPRINTER_IMPLEMENTATION",
                    "2.6",
                    "scrapy==2.6.3",
                    Issue(
                        "SCP09: future Scrapy setting: REQUEST_FINGERPRINTER_IMPLEMENTATION "
                        "(added in Scrapy 2.7.0)",
                        column=ISSUE_COLUMN,
                    ),
                ),
                (
                    "REQUEST_FINGERPRINTER_IMPLEMENTATION",
                    "2.6",
                    f"scrapy=={MINIMUM_SUPPORTED_SCRAPY_VERSION}",
                    Issue(
                        "SCP09: future Scrapy setting: REQUEST_FINGERPRINTER_IMPLEMENTATION "
                        "(added in Scrapy 2.7.0)",
                        column=ISSUE_COLUMN,
                    ),
                ),
                (
                    "LOG_UNSERIALIZABLE_REQUESTS",
                    True,
                    f"scrapy=={LATEST_KNOWN_SCRAPY_VERSION}",
                    Issue(
                        "SCP10: removed Scrapy setting: LOG_UNSERIALIZABLE_REQUESTS (removed "
                        "in Scrapy 2.1.0)",
                        column=ISSUE_COLUMN,
                    ),
                ),
                (
                    "LOG_UNSERIALIZABLE_REQUESTS",
                    True,
                    "scrapy==2.1.0",
                    Issue(
                        "SCP10: removed Scrapy setting: LOG_UNSERIALIZABLE_REQUESTS (removed "
                        "in Scrapy 2.1.0)",
                        column=ISSUE_COLUMN,
                    ),
                ),
                (
                    "LOG_UNSERIALIZABLE_REQUESTS",
                    True,
                    f"scrapy=={MINIMUM_SUPPORTED_SCRAPY_VERSION}",
                    Issue(
                        "SCP08: deprecated Scrapy setting: LOG_UNSERIALIZABLE_REQUESTS (deprecated in Scrapy 2.0.1 or earlier). Use "
                        "SCHEDULER_DEBUG instead.",
                        column=ISSUE_COLUMN,
                    ),
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
def test_main(input: Input, expected: Issue | None):
    check_input(input, expected)


class TestAllowedSettings:
    def test_unknown_setting_triggers_error_by_default(self):
        code = 'CUSTOM_SETTING = "value"'
        issues = run_checker(code, filename="settings.py")
        assert len(issues) == 1
        assert (
            issues[0][2]
            == "SCP07: unknown Scrapy setting: CUSTOM_SETTING. Did you mean PROJECT_SETTINGS?"
        )

    def test_unknown_setting_allowed_when_in_allowed_list(self):
        code = 'CUSTOM_SETTING = "value"'
        issues = run_checker(
            code, filename="settings.py", allowed_settings=["CUSTOM_SETTING"]
        )
        assert len(issues) == 0

    def test_multiple_allowed_settings(self):
        code = (
            'CUSTOM_SETTING_1 = "value1"\n'
            'CUSTOM_SETTING_2 = "value2"\n'
            'UNKNOWN_SETTING = "value3"\n'
        )
        issues = run_checker(
            code,
            filename="settings.py",
            allowed_settings=["CUSTOM_SETTING_1", "CUSTOM_SETTING_2"],
        )
        assert len(issues) == 1
        assert "UNKNOWN_SETTING" in issues[0][2]

    def test_empty_allowed_settings_behaves_like_default(self):
        code = 'CUSTOM_SETTING = "value"'
        issues_default = run_checker(code, filename="settings.py")
        issues_empty = run_checker(code, filename="settings.py", allowed_settings=[])
        assert len(issues_default) == len(issues_empty) == 1
        assert issues_default[0][2] == issues_empty[0][2]

    def test_known_scrapy_settings_still_work(self):
        code = 'BOT_NAME = "mybot"'
        issues_without = run_checker(code, filename="settings.py")
        issues_with = run_checker(
            code, filename="settings.py", allowed_settings=["SOME_OTHER_SETTING"]
        )
        assert len(issues_without) == 0
        assert len(issues_with) == 0

    def test_deprecated_setting_allowed_when_in_allowed_list(self):
        code = 'settings["REQUEST_FINGERPRINTER_IMPLEMENTATION"] = True'
        issues_without = run_checker(code, requirements="scrapy==2.12.0")
        assert len(issues_without) == 1
        assert "SCP08:" in issues_without[0][2]
        issues_with = run_checker(
            code,
            requirements="scrapy==2.12.0",
            allowed_settings=["REQUEST_FINGERPRINTER_IMPLEMENTATION"],
        )
        assert len(issues_with) == 0

    def test_future_setting_allowed_when_in_allowed_list(self):
        """Test that future settings don't trigger SCP09 when in allowed list."""
        code = 'settings["REQUEST_FINGERPRINTER_IMPLEMENTATION"] = "2.6"'
        issues_without = run_checker(code, requirements="scrapy==2.6.3")
        assert len(issues_without) == 1
        assert "SCP09:" in issues_without[0][2]
        issues_with = run_checker(
            code, allowed_settings=["REQUEST_FINGERPRINTER_IMPLEMENTATION"]
        )
        assert len(issues_with) == 0

    def test_removed_setting_allowed_when_in_allowed_list(self):
        """Test that removed settings don't trigger SCP10 when in allowed list."""
        code = 'settings["LOG_UNSERIALIZABLE_REQUESTS"] = True'
        issues_without = run_checker(code, requirements="scrapy==2.1.0")
        assert len(issues_without) == 1
        assert "SCP10:" in issues_without[0][2]
        issues_with = run_checker(
            code, allowed_settings=["LOG_UNSERIALIZABLE_REQUESTS"]
        )
        assert len(issues_with) == 0

    def test_mixed_settings_with_selective_allowlist(self):
        """Test that only specific settings in allowlist are suppressed."""
        code = (
            'UNKNOWN_SETTING_1 = "value1"\n'
            'UNKNOWN_SETTING_2 = "value2"\n'
            'settings["LOG_UNSERIALIZABLE_REQUESTS"] = True\n'
        )
        issues_without = run_checker(code, filename="settings.py")
        assert len(issues_without) >= 2
        issues_with = run_checker(
            code,
            filename="settings.py",
            allowed_settings=["UNKNOWN_SETTING_1", "LOG_UNSERIALIZABLE_REQUESTS"],
        )
        assert len(issues_with) == 1
        assert "UNKNOWN_SETTING_2" in issues_with[0][2]
