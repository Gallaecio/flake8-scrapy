from __future__ import annotations

import ast
from typing import Any, TypedDict


class Location(TypedDict):
    line: int
    column: int


class Unparseable:
    pass


UNPARSEABLE = Unparseable()


def get_method_location(node: ast.Call) -> Location:
    assert isinstance(node.func, ast.Attribute)
    assert node.func.value.end_col_offset is not None
    return {
        "line": node.func.lineno,
        "column": node.func.value.end_col_offset + 1,
    }


def get_parameter_location(
    node: ast.Call, keyword_name: str, position: int
) -> Location:
    for keyword in node.keywords:
        if keyword.arg == keyword_name and keyword.value.lineno is not None:
            return {
                "line": keyword.value.lineno,
                "column": keyword.value.col_offset,
            }
    if position < len(node.args) and node.args[position].lineno is not None:
        return {
            "line": node.args[position].lineno,
            "column": node.args[position].col_offset,
        }
    return get_method_location(node)


def load_value_from_ast(node: ast.AST | Unparseable) -> Any:
    if node is UNPARSEABLE:
        return UNPARSEABLE
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.List):
        return [load_value_from_ast(elt) for elt in node.elts]
    if isinstance(node, ast.Dict):
        keys = [load_value_from_ast(k) if k is not None else None for k in node.keys]
        values = [load_value_from_ast(v) for v in node.values]
        if UNPARSEABLE not in keys and UNPARSEABLE not in values and None not in keys:
            return dict(zip(keys, values))
    return UNPARSEABLE


def load_argument_from_call(node: ast.Call, argument_name: str, position: int) -> Any:
    if len(node.args) > position:
        return load_value_from_ast(node.args[position])

    for keyword in node.keywords:
        if keyword.arg == argument_name:
            return load_value_from_ast(keyword.value)

    return UNPARSEABLE
