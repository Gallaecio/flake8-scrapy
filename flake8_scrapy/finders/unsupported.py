from __future__ import annotations

import ast
from ast import Assign, Attribute, Call, Name, expr
from typing import TYPE_CHECKING

from . import IssueFinder

if TYPE_CHECKING:
    from collections.abc import Generator


def import_paths_from_complete(
    complete_paths: set[tuple[str, ...]],
) -> set[tuple[str, ...]]:
    """Return a set of tuple of both complete and partial import paths based on
    the provided complete import paths.

    >>> import_paths_from_complete({(("scrapy",), ("scrapy", "http"), ("scrapy", "http", "request"))})
    {('scrapy',), ('http',), ('request',), ('scrapy', 'http'), ('scrapy', 'http', 'request'), ('http', 'request')}
    """
    result = set(complete_paths)
    for complete_path in complete_paths:
        if len(complete_path) <= 1:
            continue
        for i in range(1, len(complete_path)):
            result.add(complete_path[i:])
    return result


VALID_REQUEST_IMPORT_PATHS = {
    cls: import_paths_from_complete(complete_paths)
    for cls, complete_paths in (
        ("Request", {("scrapy",), ("scrapy", "http"), ("scrapy", "http", "request")}),
        (
            "FormRequest",
            {("scrapy",), ("scrapy", "http"), ("scrapy", "http", "request", "form")},
        ),
        (
            "JsonRequest",
            {("scrapy", "http"), ("scrapy", "http", "request", "json_request")},
        ),
        ("XmlRpcRequest", {("scrapy", "http"), ("scrapy", "http", "request", "rpc")}),
    )
}


def import_path_from_attribute(attr: expr) -> tuple[str, ...]:
    """Return the import path as a tuple of strings from an Attribute node."""
    if not isinstance(attr, (Attribute, Name)):
        return ()
    parts = []
    current_attr: Attribute | Name = attr
    while isinstance(current_attr, Attribute):
        parts.append(current_attr.attr)
        if not isinstance(current_attr.value, (Attribute, Name)):
            return ()
        current_attr = current_attr.value
    if isinstance(current_attr, Name):
        parts.append(current_attr.id)
    return tuple(reversed(parts))


class LambdaCallbackIssueFinder(IssueFinder):
    msg_code = "SCP05"
    msg_info = "lambda callback"

    def looks_like_request(self, func: expr):
        return (
            isinstance(func, Name)
            and func.id
            in {
                "Request",
                "FormRequest",
                "JsonRequest",
                "XmlRpcRequest",
                # In code where different request classes are used,
                # importing scrapy.Request as ScrapyRequest is common.
                "ScrapyRequest",
            }
        ) or (
            isinstance(func, Attribute)
            and func.attr in {"Request", "FormRequest", "JsonRequest", "XmlRpcRequest"}
            and import_path_from_attribute(func.value)
            in VALID_REQUEST_IMPORT_PATHS[func.attr]
        )

    def find_issues(
        self, node: Call | Assign
    ) -> Generator[tuple[int, int, str], None, None]:
        if isinstance(node, Call):
            yield from self._find_issues_in_call(node)
        elif isinstance(node, Assign):
            yield from self._find_issues_in_assign(node)

    def _find_issues_in_call(
        self, node: Call
    ) -> Generator[tuple[int, int, str], None, None]:
        if not self.looks_like_request(node.func):
            return
        for position in (
            1,  # callback
            10,  # errback
        ):
            if len(node.args) > position:
                arg = node.args[position]
                if isinstance(arg, ast.Lambda):
                    yield (arg.lineno, arg.col_offset, self.message)
        for kw in node.keywords:
            if kw.arg in {"callback", "errback"} and isinstance(kw.value, ast.Lambda):
                yield (kw.value.lineno, kw.value.col_offset, self.message)

    def _find_issues_in_assign(
        self, node: Assign
    ) -> Generator[tuple[int, int, str], None, None]:
        # Check for assignments like obj.callback = lambda x: x or obj.errback = lambda x: x
        if not isinstance(node.value, ast.Lambda):
            return

        # Check if any target is a callback/errback attribute assignment
        has_callback_errback_target = any(
            isinstance(target, Attribute) and target.attr in {"callback", "errback"}
            for target in node.targets
        )

        if has_callback_errback_target:
            yield (node.value.lineno, node.value.col_offset, self.message)
