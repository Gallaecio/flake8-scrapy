from __future__ import annotations

from pathlib import Path

import pytest

from flake8_scrapy._finders.data import (
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
                ("BOT_NAME", "foo", None, NO_ISSUE),
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
        *(
            (
                Input(f'settings.getbool("{setting}")'),
                Issue(
                    f"SCP17: wrong setting getter: use [] or get() to read {setting}",
                    column=17,
                ),
            )
            for setting in (
                "BOT_NAME",
                "AWS_ACCESS_KEY_ID",
                "SCHEDULER",
                "JOBDIR",
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
                Input(f'settings["{setting}"] = {value!r}'),
                Issue(
                    f"SCP18: invalid setting value: {setting} {message}",
                    column=column,
                ),
            )
            for setting, value, message, column in (
                (
                    "CONCURRENT_REQUESTS",
                    None,
                    "only supports values that can be passed to int()",
                    34,
                ),
                (
                    "LOGSTATS_INTERVAL",
                    None,
                    "only supports values that can be passed to float()",
                    32,
                ),
                (
                    "LOG_VERSIONS",
                    None,
                    "only supports values that can be passed to list()",
                    27,
                ),
                ("BOT_NAME", None, "only supports string values", 23),
                ("AWS_ACCESS_KEY_ID", [], "only supports None or string values", 32),
                (
                    "SCHEDULER",
                    123,
                    "only supports class objects or strings containing class import paths",
                    24,
                ),
                ("JOBDIR", [], "only supports None, Path objects, or strings", 21),
                (
                    "ADDONS",
                    None,
                    "only supports values that can be passed to dict() or strings defining a JSON object",
                    21,
                ),
                (
                    "SPIDER_CONTRACTS",
                    None,
                    "only supports values that can be passed to dict() or strings defining a JSON object",
                    31,
                ),
                (
                    "FEED_EXPORT_FIELDS",
                    0,
                    "only supports None, str, tuple, dict, or list values",
                    33,
                ),
                (
                    "LOG_LEVEL",
                    None,
                    "only supports valid logging levels: 'CRITICAL', 'FATAL', 'ERROR', 'WARNING', 'WARN', 'INFO', 'DEBUG', 'NOTSET', 'critical', 'fatal', 'error', 'warning', 'warn', 'info', 'debug', 'notset', 50, 40, 30, 20, 10, 0 or any integer",
                    24,
                ),
                (
                    "LOG_LEVEL",
                    "FOO",
                    "only supports valid logging levels: 'CRITICAL', 'FATAL', 'ERROR', 'WARNING', 'WARN', 'INFO', 'DEBUG', 'NOTSET', 'critical', 'fatal', 'error', 'warning', 'warn', 'info', 'debug', 'notset', 50, 40, 30, 20, 10, 0 or any integer",
                    24,
                ),
                (
                    "DOWNLOADER_CLIENT_TLS_METHOD",
                    None,
                    "only supports the following values: 'TLS', 'TLSv1.0', 'TLSv1.1', 'TLSv1.2'.",
                    43,
                ),
                (
                    "DOWNLOADER_CLIENT_TLS_METHOD",
                    "TLSv1.3",
                    "only supports the following values: 'TLS', 'TLSv1.0', 'TLSv1.1', 'TLSv1.2'.",
                    43,
                ),
                (
                    "PERIODIC_LOG_DELTA",
                    False,
                    "only supports None, True, or a dict with 'include' and/or 'exclude' keys containing lists of strings",
                    33,
                ),
                (
                    "PERIODIC_LOG_DELTA",
                    "invalid",
                    "only supports None, True, or a dict with 'include' and/or 'exclude' keys containing lists of strings",
                    33,
                ),
                (
                    "PERIODIC_LOG_DELTA",
                    {"invalid_key": ["stats"]},
                    "only supports None, True, or a dict with 'include' and/or 'exclude' keys containing lists of strings",
                    33,
                ),
                (
                    "PERIODIC_LOG_DELTA",
                    {"include": "not_a_list"},
                    "only supports None, True, or a dict with 'include' and/or 'exclude' keys containing lists of strings",
                    33,
                ),
                (
                    "PERIODIC_LOG_DELTA",
                    {"include": [123]},
                    "only supports None, True, or a dict with 'include' and/or 'exclude' keys containing lists of strings",
                    33,
                ),
                (
                    "FEED_URI_PARAMS",
                    123,
                    "only supports None, callable objects, or strings containing callable import paths",
                    30,
                ),
                (
                    "FEED_URI_PARAMS",
                    "invalid",
                    "only supports None, callable objects, or strings containing callable import paths",
                    30,
                ),
                (
                    "FEED_EXPORT_INDENT",
                    "not_int",
                    "only supports None or values that can be passed to int()",
                    33,
                ),
                (
                    "FEEDS",
                    "not_a_dict",
                    "must be a dict",
                    20,
                ),
                (
                    "FEEDS",
                    [],
                    "must be a dict",
                    20,
                ),
                (
                    "FEEDS",
                    None,
                    "must be a dict",
                    20,
                ),
                (
                    "DOWNLOAD_SLOTS",
                    "not_a_dict",
                    "must be a dict",
                    29,
                ),
                (
                    "DOWNLOAD_SLOTS",
                    [],
                    "must be a dict",
                    29,
                ),
                (
                    "DOWNLOAD_SLOTS",
                    None,
                    "must be a dict",
                    29,
                ),
            )
        ),
        # SCP18: FEEDS specific validation test cases
        (
            Input('settings["FEEDS"] = {"output.json": "not_a_dict"}'),
            Issue(
                "SCP18: invalid setting value: FEEDS feed config for 'output.json' must be a dict",
                column=20,
            ),
        ),
        (
            Input('settings["FEEDS"] = {"output.json": 123}'),
            Issue(
                "SCP18: invalid setting value: FEEDS feed config for 'output.json' must be a dict",
                column=20,
            ),
        ),
        (
            Input('settings["FEEDS"] = {"output.json": []}'),
            Issue(
                "SCP18: invalid setting value: FEEDS feed config for 'output.json' must be a dict",
                column=20,
            ),
        ),
        (
            Input('settings["FEEDS"] = {"output.json": {"format": 123}}'),
            Issue(
                "SCP18: invalid setting value: FEEDS 'format' in 'output.json' must be a string",
                column=20,
            ),
        ),
        (
            Input('settings["FEEDS"] = {"output.json": {"batch_item_count": -1}}'),
            Issue(
                "SCP18: invalid setting value: FEEDS 'batch_item_count' in 'output.json' must be a non-negative integer",
                column=20,
            ),
        ),
        (
            Input(
                'settings["FEEDS"] = {"output.json": {"batch_item_count": "not_int"}}'
            ),
            Issue(
                "SCP18: invalid setting value: FEEDS 'batch_item_count' in 'output.json' must be a non-negative integer",
                column=20,
            ),
        ),
        (
            Input('settings["FEEDS"] = {"output.json": {"encoding": 123}}'),
            Issue(
                "SCP18: invalid setting value: FEEDS 'encoding' in 'output.json' must be a string or None",
                column=20,
            ),
        ),
        (
            Input(
                'settings["FEEDS"] = {"output.json": {"fields": "not_list_or_dict"}}'
            ),
            Issue(
                "SCP18: invalid setting value: FEEDS 'fields' in 'output.json' must be None, a list of strings, or a dict mapping strings to strings",
                column=20,
            ),
        ),
        (
            Input('settings["FEEDS"] = {"output.json": {"fields": [123]}}'),
            Issue(
                "SCP18: invalid setting value: FEEDS 'fields' in 'output.json' must be None, a list of strings, or a dict mapping strings to strings",
                column=20,
            ),
        ),
        (
            Input('settings["FEEDS"] = {"output.json": {"fields": {"key": 123}}}'),
            Issue(
                "SCP18: invalid setting value: FEEDS 'fields' in 'output.json' must be None, a list of strings, or a dict mapping strings to strings",
                column=20,
            ),
        ),
        (
            Input('settings["FEEDS"] = {"output.json": {"item_classes": "not_list"}}'),
            Issue(
                "SCP18: invalid setting value: FEEDS 'item_classes' in 'output.json' must be a list of class objects or class import path strings",
                column=20,
            ),
        ),
        (
            Input(
                'settings["FEEDS"] = {"output.json": {"item_classes": ["invalid_path"]}}'
            ),
            Issue(
                "SCP18: invalid setting value: FEEDS 'item_classes' in 'output.json' contains invalid import path 'invalid_path'",
                column=20,
            ),
        ),
        (
            Input(
                'settings["FEEDS"] = {"output.json": {"item_filter": "invalid_path"}}'
            ),
            Issue(
                "SCP18: invalid setting value: FEEDS 'item_filter' in 'output.json' contains invalid import path 'invalid_path'",
                column=20,
            ),
        ),
        (
            Input('settings["FEEDS"] = {"output.json": {"indent": -1}}'),
            Issue(
                "SCP18: invalid setting value: FEEDS 'indent' in 'output.json' must be a non-negative integer",
                column=20,
            ),
        ),
        (
            Input('settings["FEEDS"] = {"output.json": {"indent": "not_int"}}'),
            Issue(
                "SCP18: invalid setting value: FEEDS 'indent' in 'output.json' must be a non-negative integer",
                column=20,
            ),
        ),
        (
            Input(
                'settings["FEEDS"] = {"output.json": {"item_export_kwargs": "not_dict"}}'
            ),
            Issue(
                "SCP18: invalid setting value: FEEDS 'item_export_kwargs' in 'output.json' must be a dict",
                column=20,
            ),
        ),
        (
            Input('settings["FEEDS"] = {"output.json": {"overwrite": "not_bool"}}'),
            Issue(
                "SCP18: invalid setting value: FEEDS 'overwrite' in 'output.json' must be a boolean",
                column=20,
            ),
        ),
        (
            Input('settings["FEEDS"] = {"output.json": {"store_empty": "not_bool"}}'),
            Issue(
                "SCP18: invalid setting value: FEEDS 'store_empty' in 'output.json' must be a boolean",
                column=20,
            ),
        ),
        (
            Input('settings["FEEDS"] = {"output.json": {"uri_params": "invalid"}}'),
            Issue(
                "SCP18: invalid setting value: FEEDS 'uri_params' in 'output.json' contains invalid callable import path 'invalid'",
                column=20,
            ),
        ),
        (
            Input(
                'settings["FEEDS"] = {"output.json": {"postprocessing": ["invalid_path"]}}'
            ),
            Issue(
                "SCP18: invalid setting value: FEEDS 'postprocessing' in 'output.json' contains invalid import path 'invalid_path'",
                column=20,
            ),
        ),
        # Missing feed URL - feed config keys at top level
        (
            Input(
                'settings["FEEDS"] = {\n    "item_classes": [ProductItem],\n    "item_filter": MyFilter,\n    "uri_params": get_uri_params,\n}'
            ),
            Issue(
                "SCP18: invalid setting value: FEEDS missing feed URL: 'item_classes' appears to be a feed configuration key, but FEEDS must be a dict where keys are feed URLs (like 'output.json') and values are feed configurations",
                column=20,
            ),
        ),
        # DOWNLOAD_SLOTS: unsupported key
        (
            Input('settings["DOWNLOAD_SLOTS"] = {"toscrape.com": {"foo": "bar"}}'),
            Issue(
                "SCP18: invalid setting value: DOWNLOAD_SLOTS unknown slot config key 'foo' in 'toscrape.com', must be one of: concurrency, delay, randomize_delay",
                column=29,
            ),
        ),
        (
            Input('settings["DOWNLOAD_SLOTS"] = {"toscrape.com": {"concurrency": -1}}'),
            Issue(
                "SCP18: invalid setting value: DOWNLOAD_SLOTS 'concurrency' in 'toscrape.com' must be a positive integer (1+)",
                column=29,
            ),
        ),
        (
            Input('settings["DOWNLOAD_SLOTS"] = {"toscrape.com": {"concurrency": 0}}'),
            Issue(
                "SCP18: invalid setting value: DOWNLOAD_SLOTS 'concurrency' in 'toscrape.com' must be a positive integer (1+)",
                column=29,
            ),
        ),
        (
            Input('settings["DOWNLOAD_SLOTS"] = {"toscrape.com": {"delay": -1}}'),
            Issue(
                "SCP18: invalid setting value: DOWNLOAD_SLOTS 'delay' in 'toscrape.com' must be a positive float (0.0+)",
                column=29,
            ),
        ),
        (
            Input(
                'settings["DOWNLOAD_SLOTS"] = {"toscrape.com": {"randomize_delay": 1}}'
            ),
            Issue(
                "SCP18: invalid setting value: DOWNLOAD_SLOTS 'randomize_delay' in 'toscrape.com' must be a boolean",
                column=29,
            ),
        ),
        # FEEDS future keys - testing version-based validation
        (
            Input(
                'settings["FEEDS"] = {"output.json": {"batch_item_count": 100}}',
                requirements="scrapy==2.2.0",
            ),
            Issue(
                "SCP18: invalid setting value: FEEDS 'batch_item_count' in 'output.json' is not available in Scrapy 2.2.0, requires Scrapy 2.3.0 or later",
                column=20,
            ),
        ),
        (
            Input(
                'settings["FEEDS"] = {"output.json": {"item_classes": ["myproject.items.Item"]}}',
                requirements="scrapy==2.5.0",
            ),
            Issue(
                "SCP18: invalid setting value: FEEDS 'item_classes' in 'output.json' is not available in Scrapy 2.5.0, requires Scrapy 2.6.0 or later",
                column=20,
            ),
        ),
        (
            Input(
                'settings["FEEDS"] = {"output.json": {"item_filter": "myproject.filters.Filter"}}',
                requirements="scrapy==2.5.0",
            ),
            Issue(
                "SCP18: invalid setting value: FEEDS 'item_filter' in 'output.json' is not available in Scrapy 2.5.0, requires Scrapy 2.6.0 or later",
                column=20,
            ),
        ),
        (
            Input(
                'settings["FEEDS"] = {"output.json": {"item_export_kwargs": {"root": "items"}}}',
                requirements="scrapy==2.3.0",
            ),
            Issue(
                "SCP18: invalid setting value: FEEDS 'item_export_kwargs' in 'output.json' is not available in Scrapy 2.3.0, requires Scrapy 2.4.0 or later",
                column=20,
            ),
        ),
        (
            Input(
                'settings["FEEDS"] = {"output.json": {"overwrite": True}}',
                requirements="scrapy==2.3.0",
            ),
            Issue(
                "SCP18: invalid setting value: FEEDS 'overwrite' in 'output.json' is not available in Scrapy 2.3.0, requires Scrapy 2.4.0 or later",
                column=20,
            ),
        ),
        (
            Input(
                'settings["FEEDS"] = {"output.json": {"postprocessing": ["myproject.processors.Processor"]}}',
                requirements="scrapy==2.5.0",
            ),
            Issue(
                "SCP18: invalid setting value: FEEDS 'postprocessing' in 'output.json' is not available in Scrapy 2.5.0, requires Scrapy 2.6.0 or later",
                column=20,
            ),
        ),
        # Valid when Scrapy version is sufficient
        (
            Input(
                'settings["FEEDS"] = {"output.json": {"batch_item_count": 100}}',
                requirements="scrapy==2.3.0",
            ),
            NO_ISSUE,
        ),
        (
            Input(
                'settings["FEEDS"] = {"output.json": {"item_classes": ["myproject.items.Item"]}}',
                requirements="scrapy==2.6.0",
            ),
            NO_ISSUE,
        ),
        (
            Input(
                'settings["FEEDS"] = {"output.json": {"overwrite": True}}',
                requirements="scrapy==2.4.0",
            ),
            NO_ISSUE,
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
                ("BOT_NAME", "mybot"),
                ("AWS_ACCESS_KEY_ID", None),
                ("AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE"),
                ("JOBDIR", None),
                ("JOBDIR", "/tmp/foo"),
                ("JOBDIR", Path("/tmp/foo")),
                ("LOG_LEVEL", "INFO"),
                ("LOG_LEVEL", "debug"),
                ("LOG_LEVEL", 20),
                ("LOG_LEVEL", 0),
                ("LOG_LEVEL", 25),
                ("DOWNLOADER_CLIENT_TLS_METHOD", "TLS"),
                ("DOWNLOADER_CLIENT_TLS_METHOD", "TLSv1.2"),
                ("PERIODIC_LOG_DELTA", None),
                ("PERIODIC_LOG_DELTA", True),
                ("PERIODIC_LOG_DELTA", {"include": ["stats"]}),
                ("PERIODIC_LOG_DELTA", {"exclude": ["downloader/response_count"]}),
                ("PERIODIC_LOG_DELTA", {"include": ["stats"], "exclude": ["other"]}),
                ("PERIODIC_LOG_DELTA", {"include": []}),
                ("PERIODIC_LOG_DELTA", {"exclude": []}),
                ("PERIODIC_LOG_DELTA", {}),
                ("FEED_URI_PARAMS", None),
                ("FEED_URI_PARAMS", "myproject.utils.get_uri_params"),
                ("FEED_EXPORT_INDENT", None),
                ("FEED_EXPORT_INDENT", 0),
                ("FEED_EXPORT_INDENT", 1),
                ("FEED_EXPORT_INDENT", "2"),
                ("FEED_EXPORT_INDENT", True),
                ("FEEDS", {}),
                ("FEEDS", "{}"),
                ("FEEDS", {"output.json": {"format": "json"}}),
                ("FEEDS", '{"output.json": {"format": "json"}}'),
                (
                    "FEEDS",
                    {
                        "output.csv": {
                            "format": "csv",
                            "fields": ["name", "price"],
                            "encoding": "utf-8",
                        }
                    },
                ),
                (
                    "FEEDS",
                    {
                        "output.xml": {
                            "format": "xml",
                            "batch_item_count": 100,
                            "encoding": None,
                            "fields": {
                                "name": "product_name",
                                "price": "product_price",
                            },
                            "item_classes": ["myproject.items.ProductItem"],
                            "item_filter": "myproject.filters.MyFilter",
                            "indent": 2,
                            "item_export_kwargs": {"root_element": "products"},
                            "overwrite": True,
                            "store_empty": False,
                            "uri_params": "myproject.utils.get_uri_params",
                        }
                    },
                ),
                (
                    "FEEDS",
                    {
                        "output.json": {
                            "format": "json",
                            "batch_item_count": 0,
                            "indent": 0,
                            "fields": None,
                        }
                    },
                ),
                ("DOWNLOAD_SLOTS", {}),
                ("DOWNLOAD_SLOTS", "{}"),
                ("DOWNLOAD_SLOTS", {"toscrape.com": {}}),
                ("DOWNLOAD_SLOTS", {"toscrape.com": {"concurrency": 1}}),
                ("DOWNLOAD_SLOTS", {"toscrape.com": {"delay": 0.0}}),
                ("DOWNLOAD_SLOTS", {"toscrape.com": {"randomize_delay": True}}),
                ("DOWNLOAD_SLOTS", '{"toscrape.com": {"concurrency": 1}}'),
            )
        ),
        *(
            (
                Input(f'settings["{setting}"] = {value}'),
                NO_ISSUE,
            )
            for setting, value in (
                ("SCHEDULER", "CustomScheduler"),
                ("FEED_URI_PARAMS", "uri_params"),
            )
        ),
        (
            Input(
                'settings["FEEDS"] = {\n'
                '    "output.jsonl": {\n'
                '        "item_classes": [ProductItem],\n'
                '        "item_filter": MyFilter,\n'
                '        "uri_params": get_uri_params,\n'
                "    }\n"
                "}\n"
            ),
            NO_ISSUE,
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
        # SCP25
        *(
            (
                Input(syntax),
                Issue(
                    f"SCP25: unneeded get(): use [] instead of get() to read {setting}",
                    column=13,
                ),
            )
            for setting in (
                "AWS_ACCESS_KEY_ID",  # Not in scrapy.settings.default_settings
                "BOT_NAME",  # Non-None in scrapy.settings.default_settings
                "FEED_EXPORT_ENCODING",  # None in scrapy.settings.default_settings
            )
            for syntax in (
                f"settings.get({setting!r})",
                f"settings.get({setting!r}, None)",
            )
        ),
        # SCP26
        *(
            (
                Input(syntax),
                issue,
            )
            for syntax, issue in (
                # get() getter
                # Not in scrapy.settings.default_settings
                ("settings.get('AWS_ACCESS_KEY_ID', 'foo')", NO_ISSUE),
                # Non-None in scrapy.settings.default_settings
                (
                    "settings.get('BOT_NAME', 'foo')",
                    Issue(
                        "SCP26: ignored getter default: BOT_NAME is set in "
                        "scrapy.settings.default_settings with a non-None "
                        "value, so the default value passed to get() "
                        "will never be used.",
                        column=25,
                    ),
                ),
                # None in scrapy.settings.default_settings
                ("settings.get('FEED_EXPORT_ENCODING', 'foo')", NO_ISSUE),
                # Other getters
                # Not in scrapy.settings.default_settings
                ("settings.getbool('AWS_USE_SSL', 'foo')", NO_ISSUE),
                # Non-None in scrapy.settings.default_settings
                (
                    "settings.getbool('AUTOTHROTTLE_ENABLED', 'foo')",
                    Issue(
                        "SCP26: ignored getter default: "
                        "AUTOTHROTTLE_ENABLED is set in "
                        "scrapy.settings.default_settings with a non-None "
                        "value, so the default value passed to getbool() "
                        "will never be used.",
                        column=41,
                    ),
                ),
                # None does not apply, since almost any value that can be None
                # must use get().
            )
        ),
        # SCP27: unnecessary import path strings
        *(
            (
                Input(f"{setting} = {value}", filename="settings.py"),
                Issue(
                    f"SCP27: import path string in setting: {setting} should import the class directly instead of using import path string",
                    column=len(setting) + 3,
                ),
            )
            for setting, value in [
                ("DOWNLOADER", repr("custom.Downloader")),
            ]
        ),
        # SCP27: potentially necessary import path strings
        (
            # Based dicts may need import path strings to disable or change the
            # priority of built-in keys from the base setting.
            Input(
                "SPIDER_MIDDLEWARES = "
                '{"scrapy.spidermiddlewares.httperror.HttpErrorMiddleware": None}',
                filename="settings.py",
            ),
            NO_ISSUE,
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
