from __future__ import annotations

from typing import TYPE_CHECKING

from . import NO_ISSUE, File, Issue, cases
from .helpers import check_project

if TYPE_CHECKING:
    from collections.abc import Sequence

ALL_REQUEST_CLASSES = (
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
REPRESENTATIVE_REQUEST_CLASSES = (
    "Request",
    "scrapy.http.request.json_request.JsonRequest",
)
ALL_NON_REQUEST_CLASSES = (
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
            # All possible request classes are taken into account. Other
            # classes are ignored.
            *(
                (
                    f"{cls}(url, lambda x: x)",
                    Issue("SCP05 lambda callback", column=len(cls) + 6, path=path),
                )
                for cls in ALL_REQUEST_CLASSES
            ),
            *(
                (f"{cls}(url, lambda x: x)", NO_ISSUE)
                for cls in ALL_NON_REQUEST_CLASSES
            ),
            # No callback or errback params
            *((f"{cls}(url)", NO_ISSUE) for cls in REPRESENTATIVE_REQUEST_CLASSES),
            # Combinations of callback and errback params
            *(
                (
                    f"{cls}(url, {callback_prefix}{callback}, {errback_prefix}{errback})",
                    [*callback_issues, *errback_issues],
                )
                for cls in REPRESENTATIVE_REQUEST_CLASSES
                for callback_prefix, errback_prefix in (
                    ("", "errback="),
                    ("callback=", "errback="),
                    ("", "'GET', None, None, None, None, 'utf-8', 0, False, "),
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
