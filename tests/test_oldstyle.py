from . import NO_ISSUE, File, Issue, cases
from .helpers import check_project


@cases(
    [
        # SCP03 urljoin issues
        *(
            (
                File(code, path),
                Issue(
                    'SCP03 urljoin(response.url, "/foo") can be replaced by response.urljoin("/foo")',
                    path=path,
                    column=column,
                ),
            )
            for path in ("a.py",)
            for code, column in (
                ('urljoin(response.url, "/foo")', 0),
                ('url = urljoin(response.url, "/foo")', 6),
            )
        ),
        *(
            (File(code, path), NO_ISSUE)
            for path in ("a.py",)
            for code in (
                'response.urljoin("/foo")',
                "url = urljoin()",
                "test.py",
                'urljoin(x, "/foo")',
                "test.py",
                'urljoin(x.y.z, "/foo")',
            )
        ),
        # SCP04 selector issues
        *(
            (
                File(code, path),
                Issue(
                    "SCP04 use response.selector or response.xpath or response.css instead",
                    path=path,
                ),
            )
            for path in ("a.py",)
            for code in (
                "sel = Selector(response)",
                'sel = Selector(response, type="html")',
                'sel = Selector(response=response, type="html")',
                "sel = Selector(response=response)",
                "sel = Selector(text=response.text)",
                "sel = Selector(text=response.body)",
                "sel = Selector(text=response.body_as_unicode())",
                'sel = Selector(text=response.text, type="html")',
            )
        ),
        *(
            (File(code, path), NO_ISSUE)
            for path in ("a.py",)
            for code in (
                "sel = Selector(get_text())",
                "sel = Selector(self.get_text())",
            )
        ),
    ]
)
def test_oldstyle(input, expected):
    check_project(input, expected)
