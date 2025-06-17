from . import NO_ISSUE, File, Issue, cases
from .helpers import check_project


@cases(
    [
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
    ]
)
def test_settings(input, expected):
    check_project(input, expected)
