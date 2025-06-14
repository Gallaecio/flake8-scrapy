from __future__ import annotations

from typing import TYPE_CHECKING

from . import NO_ISSUE, File, Issue, cases
from .helpers import check_project

if TYPE_CHECKING:
    from collections.abc import Sequence

REQUEST_CLASSES = (
    "Request",
    "scrapy.Request",
    "scrapy.http.Request",
    "http.Request",
    "scrapy.http.request.Request",
    "http.request.Request",
    "request.Request",
    "FormRequest",
    "scrapy.FormRequest",
    "scrapy.http.FormRequest",
    "http.FormRequest",
    "scrapy.http.request.form.FormRequest",
    "http.request.form.FormRequest",
    "request.form.FormRequest",
    "form.FormRequest",
    "JsonRequest",
    "scrapy.http.JsonRequest",
    "http.JsonRequest",
    "scrapy.http.request.json_request.JsonRequest",
    "http.request.json_request.JsonRequest",
    "request.json_request.JsonRequest",
    "json_request.JsonRequest",
    "XmlRpcRequest",
    "scrapy.http.XmlRpcRequest",
    "http.XmlRpcRequest",
    "scrapy.http.request.rpc.XmlRpcRequest",
    "http.request.rpc.XmlRpcRequest",
    "request.rpc.XmlRpcRequest",
    "rpc.XmlRpcRequest",
    "ScrapyRequest",
)
NON_REQUEST_CLASSES = (
    "foo.Request",
    # Long import paths should not trigger issues.
    "a.b.c.d.e.f.g.Request",
)
NON_LAMBDA_CALLBACKS = (
    "self.foo",
    "foo",
    "'foo'",
    "None",
    "NO_CALLBACK",
    "scrapy.http.request.NO_CALLBACK",
)

CASES = (
    *(
        (File(code, path=path), issues)
        for path in ("a.py",)
        for code, issues in (
            # No callback or errback params
            *(
                (f"{cls}(url)", NO_ISSUE)
                for cls in (*REQUEST_CLASSES, *NON_REQUEST_CLASSES)
            ),
            # Combinations of callback and errback params
            *(
                (
                    f"{cls}(url, {callback_prefix}{callback}, {errback_prefix}{errback}{suffix})",
                    [*callback_issues, *errback_issues]
                    if cls_is_valid_target
                    else NO_ISSUE,
                )
                for cls, cls_is_valid_target in (
                    *((cls, True) for cls in REQUEST_CLASSES),
                    *((cls, False) for cls in NON_REQUEST_CLASSES),
                )
                for callback_prefix, errback_prefix, suffix in (
                    ("", "errback=", ""),
                    ("", "'GET', errback=", ""),
                    ("", "'GET', None, None, None, None, 'utf-8', 0, False, ", ""),
                    (
                        "",
                        "'GET', None, None, None, None, 'utf-8', 0, False, ",
                        # Test with all possible parameters +1, i.e. subclasses
                        # that extend __init__ positional parameters should
                        # work.
                        ", None, None, None",
                    ),
                    ("callback=", "errback=", ""),
                )
                for callback, callback_issues in (
                    (
                        "lambda x: x",
                        [
                            Issue(
                                "SCP05 lambda callback",
                                column=len(cls) + len(callback_prefix) + 6,
                                path=path,
                            )
                        ],
                    ),
                    *((cb, []) for cb in NON_LAMBDA_CALLBACKS),
                )
                for errback, errback_issues in (
                    (
                        "lambda x: x",
                        [
                            Issue(
                                "SCP05 lambda callback",
                                column=len(cls)
                                + len(callback_prefix)
                                + len(callback)
                                + len(errback_prefix)
                                + 8,
                                path=path,
                            )
                        ],
                    ),
                    *((cb, []) for cb in NON_LAMBDA_CALLBACKS),
                )
            ),
            # Classes with an import path including attribute objects with a
            # value that is neither a Name nor an Attribute, e.g. a Subscript,
            # are ignored.
            ("a[0].Request(url, callback=lambda x: x)", NO_ISSUE),
            ("a[0].b.Request(url, callback=lambda x: x)", NO_ISSUE),
        )
    ),
)


@cases(CASES)
def test(input: File | Sequence[File], expected: Issue | Sequence[Issue] | None):
    check_project(input, expected)
