from . import NO_ISSUE, File, Issue, cases
from .helpers import check_project

CASES = (
    # Setting object detection
    *(
        (File(code, path), NO_ISSUE)
        for path in ("a.py",)
        for code in (
            'foo.get("FOO")',
            'my_settings.get("FOO")',
        )
    ),
    # SCP28: unneeded setting get
    *(
        (
            File(code, path),
            Issue("SCP28 unneeded setting get", column=column, path=path),
        )
        for path in ("a.py",)
        for code, column in (
            ('settings.get("BOT_NAME")', 9),
            ('settings.get(name="BOT_NAME")', 9),
        )
    ),
    *(
        (File(code, path), NO_ISSUE)
        for path in ("a.py",)
        for code in (
            'settings["BOT_NAME"]',
            'settings.get("BOT_NAME", "foo")',
            'settings.get("BOT_NAME", default="foo")',
            'settings.getint("RETRY_TIMES")',
        )
    ),
    # SCP29: no-op setting getter default
    *(
        (
            File(code, path),
            Issue("SCP29 no-op setting getter default", column=column, path=path),
        )
        for path in ("a.py",)
        for code, column in (
            # get() with None default
            ('settings.get("FOO", None)', 20),
            ('settings.get("FOO", default=None)', 28),
            # getbool() with False default
            ('settings.getbool("DEBUG", False)', 26),
            ('settings.getbool("DEBUG", default=False)', 34),
            # getbool() with string that converts to False
            ('settings.getbool("DEBUG", "false")', 26),
            ('settings.getbool("DEBUG", "False")', 26),
            # getint() with 0 default
            ('settings.getint("RETRY_TIMES", 0)', 31),
            ('settings.getint("RETRY_TIMES", default=0)', 39),
            # getfloat() with 0.0 default
            ('settings.getfloat("DELAY", 0.0)', 27),
            ('settings.getfloat("DELAY", default=0.0)', 35),
            # getlist() with None default
            ('settings.getlist("DOMAINS", None)', 28),
            ('settings.getlist("DOMAINS", default=None)', 36),
            # getdict() with None default
            ('settings.getdict("CONFIG", None)', 27),
            ('settings.getdict("CONFIG", default=None)', 35),
            # getdictorlist() with None default
            ('settings.getdictorlist("DATA", None)', 31),
            ('settings.getdictorlist("DATA", default=None)', 39),
        )
    ),
    *(
        (File(code, path), NO_ISSUE)
        for path in ("a.py",)
        for code in (
            # Non-default values
            'settings.get("FOO", "default")',
            'settings.getbool("DEBUG", True)',
            'settings.getint("RETRY_TIMES", 3)',
            'settings.getfloat("DELAY", 1.5)',
            'settings.getlist("DOMAINS", [])',
            'settings.getdict("CONFIG", {})',
            'settings.getdictorlist("DATA", {})',
            # No default specified
            'settings.getbool("DEBUG")',
            'settings.getint("RETRY_TIMES")',
        )
    ),
    # SCP30: wrong setting getter
    *(
        (
            File(code, path),
            Issue("SCP30 wrong setting getter", column=column, path=path),
        )
        for path in ("a.py",)
        for code, column in (
            # Using subscript for typed settings
            ('settings["RETRY_TIMES"]', 0),
            ('settings["DOWNLOAD_DELAY"]', 0),
            ('settings["AUTOTHROTTLE_DEBUG"]', 0),
            # Using wrong getter for setting type
            ('settings.getbool("RETRY_TIMES")', 9),
            ('settings.getint("DOWNLOAD_DELAY")', 9),
            ('settings.getfloat("AUTOTHROTTLE_DEBUG")', 9),
            ('settings.getlist("RETRY_TIMES")', 9),
            ('settings.getdict("DOWNLOAD_DELAY")', 9),
            ('settings.getdictorlist("AUTOTHROTTLE_DEBUG")', 9),
        )
    ),
    *(
        (
            File(code, path),
            (
                Issue("SCP28 unneeded setting get", column=column, path=path),
                Issue("SCP30 wrong setting getter", column=column, path=path),
            ),
        )
        for path in ("a.py",)
        for code, column in (
            # Using get() for typed settings
            ('settings.get("RETRY_TIMES")', 9),
            ('settings.get("DOWNLOAD_DELAY")', 9),
            ('settings.get("AUTOTHROTTLE_DEBUG")', 9),
        )
    ),
    *(
        (File(code, path), NO_ISSUE)
        for path in ("a.py",)
        for code in (
            # Correct getter for setting type
            'settings.getint("RETRY_TIMES")',
            'settings.getfloat("DOWNLOAD_DELAY")',
            'settings.getbool("AUTOTHROTTLE_DEBUG")',
            'settings.getlist("RETRY_HTTP_CODES")',
            'settings.getdict("ADDONS")',
            'settings.getdictorlist("FEED_EXPORT_FIELDS")',
            'settings.getwithbase("EXTENSIONS")',
            # Using subscript for untyped settings
            'settings["UNKNOWN_SETTING"]',
            # Using subscript for settings that allow it (non-typed)
            'settings["BOT_NAME"]',
        )
    ),
    *(
        (
            File(code, path),
            (Issue("SCP28 unneeded setting get", column=column, path=path),),
        )
        for path in ("a.py",)
        for code, column in (
            # Using get() for untyped settings
            ('settings.get("UNKNOWN_SETTING")', 9),
            # Using get() for settings that allow it (non-typed)
            ('settings.get("BOT_NAME")', 9),
        )
    ),
)


@cases(CASES)
def test_settings(input, expected):
    check_project(input, expected)
