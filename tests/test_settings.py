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
                (
                    "SCRAPY_POET_OVERRIDES",
                    {},
                    "scrapy-poet==0.8.0",
                    NO_ISSUE,
                ),
                (
                    "SCRAPY_POET_OVERRIDES",
                    {},
                    "scrapy-poet==0.9.0",
                    Issue(
                        "SCP08: deprecated setting: SCRAPY_POET_OVERRIDES (deprecated in scrapy-poet 0.9.0). Use SCRAPY_POET_DISCOVER and/or SCRAPY_POET_RULES instead",
                        column=ISSUE_COLUMN,
                    ),
                ),
                (
                    "SCRAPY_POET_CACHE",
                    True,
                    "scrapy==2.11.0",
                    Issue(
                        "SCP15: setting for package not in requirements.txt: SCRAPY_POET_CACHE (package: scrapy-poet)",
                        column=ISSUE_COLUMN,
                    ),
                ),
                (
                    "PLAYWRIGHT_BROWSER_TYPE",
                    "chromium",
                    "scrapy==2.11.0",
                    Issue(
                        "SCP15: setting for package not in requirements.txt: PLAYWRIGHT_BROWSER_TYPE (package: scrapy-playwright)",
                        column=ISSUE_COLUMN,
                    ),
                ),
                (
                    "REDIS_HOST",
                    "localhost",
                    "scrapy==2.11.0",
                    Issue(
                        "SCP15: setting for package not in requirements.txt: REDIS_HOST (package: scrapy-redis)",
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
        # SCP17: Supported getter syntaxes
        *(
            (
                Input(syntax),
                Issue(
                    "SCP17: wrong setting getter: use getbool() to read "
                    "AUTOTHROTTLE_ENABLED",
                    column=column,
                ),
            )
            for syntax, column in (
                ('settings.get("AUTOTHROTTLE_ENABLED")', 13),
                ('settings.get(name="AUTOTHROTTLE_ENABLED")', 18),
                ('settings["AUTOTHROTTLE_ENABLED"]', 9),
            )
        ),
        # SCP17: Supported types (bool excluded, already tested above)
        *(
            (
                Input(f'settings["{setting}"]'),
                Issue(
                    f"SCP17: wrong setting getter: use {method}() to read {setting}",
                    column=ISSUE_COLUMN,
                ),
            )
            for setting, method in (
                ("CONCURRENT_REQUESTS", "getint"),
                ("LOGSTATS_INTERVAL", "getfloat"),
                ("LOG_VERSIONS", "getlist"),
                ("ADDONS", "getdict"),
                ("FEED_EXPORT_FIELDS", "getdictorlist"),
                ("SPIDER_CONTRACTS", "getwithbase"),
            )
        ),
        # SCP18: Supported setter syntaxes
        *(
            (
                Input(syntax, filename=filename),
                Issue(
                    "SCP18: invalid setting value: AUTOTHROTTLE_ENABLED only "
                    "supports the following values: True, False, 0, 1, "
                    "'True', 'False', 'true', 'false', '0', '1'.",
                    column=column,
                ),
            )
            for syntax, column, filename in (
                ('settings["AUTOTHROTTLE_ENABLED"] = "foo"', 35, None),
                ('AUTOTHROTTLE_ENABLED = "foo"', 23, "settings.py"),
                ('settings.set("AUTOTHROTTLE_ENABLED", "foo")', 37, None),
                ('settings.setdefault("AUTOTHROTTLE_ENABLED", "foo")', 44, None),
                ('settings.setdict({"AUTOTHROTTLE_ENABLED": "foo"})', 42, None),
                ('settings.update({"AUTOTHROTTLE_ENABLED": "foo"})', 41, None),
            )
        ),
        # SCP18: Supported types (bool excluded, already tested above)
        *(
            (
                Input(f'settings["{setting}"] = None'),
                Issue(
                    f"SCP18: invalid setting value: {setting} only supports "
                    f"values that can be passed to {cls}()",
                    column=column,
                ),
            )
            for setting, cls, column in (
                ("CONCURRENT_REQUESTS", "int", 34),
                ("LOGSTATS_INTERVAL", "float", 32),
                ("LOG_VERSIONS", "list", 27),
            )
        ),
        *(
            (
                Input(f'settings["{setting}"] = None'),
                Issue(
                    f"SCP18: invalid setting value: {setting} only supports "
                    f"values that can be passed to dict() or strings defining a "
                    "JSON object",
                    column=column,
                ),
            )
            for setting, column in (("ADDONS", 21), ("SPIDER_CONTRACTS", 31))
        ),
        (
            Input('settings["FEED_EXPORT_FIELDS"] = 0'),
            Issue(
                "SCP18: invalid setting value: FEED_EXPORT_FIELDS only "
                "supports None, str, tuple, dict, or list values",
                column=33,
            ),
        ),
        # SCP18: Ignored (valid) values
        *(
            (
                Input(f'settings["{setting}"] = {value!r}'),
                NO_ISSUE,
            )
            for setting, value in (
                ("CONCURRENT_REQUESTS", 1),
                ("CONCURRENT_REQUESTS", 1.0),
                ("CONCURRENT_REQUESTS", True),
                ("CONCURRENT_REQUESTS", "1"),
                ("CONCURRENT_REQUESTS", b"1"),
                ("LOGSTATS_INTERVAL", 1.0),
                ("LOGSTATS_INTERVAL", 1),
                ("LOGSTATS_INTERVAL", True),
                ("LOGSTATS_INTERVAL", "1.0"),
                ("LOGSTATS_INTERVAL", b"1.0"),
                ("LOG_VERSIONS", []),
                ("LOG_VERSIONS", ["foo"]),
                ("LOG_VERSIONS", ["foo", "bar"]),
                ("LOG_VERSIONS", ()),
                ("LOG_VERSIONS", set()),
                ("LOG_VERSIONS", "foo"),
                ("LOG_VERSIONS", "foo,bar"),
                ("LOG_VERSIONS", {}),
                ("LOG_VERSIONS", range(2)),
                ("ADDONS", {}),
                ("ADDONS", "{}"),
                ("FEED_EXPORT_FIELDS", None),
                ("FEED_EXPORT_FIELDS", "foo"),
                ("FEED_EXPORT_FIELDS", ()),
                ("FEED_EXPORT_FIELDS", {}),
                ("FEED_EXPORT_FIELDS", []),
                ("SPIDER_CONTRACTS", {}),
                ("SPIDER_CONTRACTS", "{}"),
            )
        ),
        # SCP22: flagged values.
        *(
            (
                Input(f'settings["USER_AGENT"] = {value!r}'),
                Issue(
                    "SCP22: USER_AGENT does not seem to provide contact "
                    "information. Put an URL, email address or phone number "
                    "in it so that web masters of target websites may contact "
                    "you.",
                    column=25,
                ),
            )
            for value in (
                "foo",
                "Jane Doe",
                "my_project (+http://www.yourdomain.com)",
                "Scrapy/2.11.2 (+https://scrapy.org)",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64; rv:139.0) Gecko/20100101 Firefox/139.0",
                "",
                None,
            )
        ),
        # SCP22: valid values.
        *(
            (
                Input(f'settings["USER_AGENT"] = {value!r}'),
                NO_ISSUE,
            )
            for value in (
                "Jane Doe (+https://jane.doe.example)",
                "jane.doe@example.com",
                "555-9292",
            )
        ),
        # SCP23
        (
            Input('BOT_NAME = "foo"', filename="settings.py"),
            NO_ISSUE,
        ),
        (
            Input('BOT_NAME = "foo"\nBOT_NAME = "bar"', filename="settings.py"),
            Issue("SCP23: BOT_NAME is set multiple times in settings.py", line=2),
        ),
        # SCP24
        (
            Input("DOWNLOAD_HANDLERS_BASE = {}", filename="settings.py"),
            Issue(
                "SCP24: use of BASE setting: do not use DOWNLOAD_HANDLERS_BASE, use DOWNLOAD_HANDLERS instead"
            ),
        ),
    ],
)
def test_main(input: Input, expected: Issue | None):
    check_input(input, expected)


@pytest.mark.parametrize(
    ("input", "expected"),
    [
        (
            Input(""),
            NO_ISSUE,
        ),
        (
            Input(
                'USER_AGENT = "Jane Doe (+https://jane.doe.example)"\n'
                "ROBOTSTXT_OBEY = True\n"
                "AUTOTHROTTLE_ENABLED = True",
                filename="settings.py",
            ),
            NO_ISSUE,
        ),
        (
            Input(
                'USER_AGENT = "Jane Doe (+https://jane.doe.example)"\n'
                "ROBOTSTXT_OBEY = True\n"
                "CONCURRENT_REQUESTS = 1\n"
                "CONCURRENT_REQUESTS_PER_DOMAIN = 1\n"
                "DOWNLOAD_DELAY = 5",
                filename="settings.py",
            ),
            NO_ISSUE,
        ),
        (
            Input("", filename="settings.py"),
            [
                Issue("SCP19: No USER_AGENT in settings.py"),
                Issue("SCP20: ROBOTSTXT_OBEY not enabled in settings.py"),
                Issue(
                    "SCP21: Incomplete throttling config in settings.py: enable AUTOTHROTTLE_ENABLED or set the following settings: CONCURRENT_REQUESTS, CONCURRENT_REQUESTS_PER_DOMAIN, DOWNLOAD_DELAY"
                ),
            ],
        ),
        (
            Input(
                'USER_AGENT = "Jane Doe (+https://jane.doe.example)"\n'
                "ROBOTSTXT_OBEY = False\n"
                "AUTOTHROTTLE_ENABLED = True",
                filename="settings.py",
            ),
            Issue("SCP20: ROBOTSTXT_OBEY not enabled in settings.py"),
        ),
        (
            Input(
                'USER_AGENT = "Jane Doe (+https://jane.doe.example)"\n'
                "ROBOTSTXT_OBEY = True\n"
                "AUTOTHROTTLE_ENABLED = False",
                filename="settings.py",
            ),
            Issue(
                "SCP21: Incomplete throttling config in settings.py: enable AUTOTHROTTLE_ENABLED or set the following settings: CONCURRENT_REQUESTS, CONCURRENT_REQUESTS_PER_DOMAIN, DOWNLOAD_DELAY"
            ),
        ),
        (
            Input(
                'USER_AGENT = "Jane Doe (+https://jane.doe.example)"\n'
                "ROBOTSTXT_OBEY = True\n"
                "CONCURRENT_REQUESTS_PER_DOMAIN = 1\n"
                "DOWNLOAD_DELAY = 5",
                filename="settings.py",
            ),
            Issue(
                "SCP21: Incomplete throttling config in settings.py: enable AUTOTHROTTLE_ENABLED or set the following settings: CONCURRENT_REQUESTS"
            ),
        ),
        (
            Input(
                'USER_AGENT = "Jane Doe (+https://jane.doe.example)"\n'
                "ROBOTSTXT_OBEY = True\n"
                "CONCURRENT_REQUESTS = 1\n"
                "DOWNLOAD_DELAY = 5",
                filename="settings.py",
            ),
            Issue(
                "SCP21: Incomplete throttling config in settings.py: enable AUTOTHROTTLE_ENABLED or set the following settings: CONCURRENT_REQUESTS_PER_DOMAIN"
            ),
        ),
        (
            Input(
                'USER_AGENT = "Jane Doe (+https://jane.doe.example)"\n'
                "ROBOTSTXT_OBEY = True\n"
                "CONCURRENT_REQUESTS = 1\n"
                "CONCURRENT_REQUESTS_PER_DOMAIN = 1",
                filename="settings.py",
            ),
            Issue(
                "SCP21: Incomplete throttling config in settings.py: enable AUTOTHROTTLE_ENABLED or set the following settings: DOWNLOAD_DELAY"
            ),
        ),
    ],
)
def test_global_settings(input: Input, expected: Issue | None):
    check_input(input, expected, enable_global_checks=True)


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
