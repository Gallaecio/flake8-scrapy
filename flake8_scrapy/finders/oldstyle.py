import ast
from collections.abc import Generator

from flake8_scrapy.issues import Issue


class UrlJoinIssueFinder:
    visit_types: tuple[str, ...] = ("Call",)

    def find_issues(self, node) -> Generator[Issue, None, None]:
        if not self.issue_applies(node):
            return

        first_param = node.args[0]
        if not isinstance(first_param, ast.Attribute) or not isinstance(
            first_param.value, ast.Name
        ):
            return

        if first_param.value.id == "response" and first_param.attr == "url":
            # found it: first param to urljoin is response.url
            yield Issue(
                code=3,
                summary='urljoin(response.url, "/foo") can be replaced by response.urljoin("/foo")',
                line=node.lineno,
                column=node.col_offset,
            )

    def issue_applies(self, node):
        return (
            isinstance(node.func, ast.Name) and node.func.id == "urljoin" and node.args
        )


class OldSelectorIssueFinder:
    visit_types: tuple[str, ...] = ("Assign",)

    def is_response_dot_body_as_unicode(self, node):
        """Returns True if node represents response.body_as_unicode()"""
        return (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "response"
            and node.func.attr == "body_as_unicode"
        )

    def is_response_dot_text_or_body(self, node):
        """Return whether or not a node represents response.text or
        response.body
        """
        return (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "response"
            and node.attr in ("text", "body")
        )

    def is_response(self, node):
        """Check if node represents an object named as response"""
        return isinstance(node, ast.Name) and node.id == "response"

    def has_response_for_keyword_parameter(self, node):
        """Check if response or response.text is passed as a keyword parameter
        as in: Selector(text=response.text) or Selector(response=response)
        """
        return (
            (node.arg == "text" and self.is_response_dot_text_or_body(node.value))
            or self.is_response_dot_body_as_unicode(node.value)
        ) or (node.arg == "response" and self.is_response(node.value))

    def issue_applies(self, node):
        return (
            isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "Selector"
        )

    def find_issues(self, node) -> Generator[Issue, None, None]:
        if not self.issue_applies(node):
            return

        # look for: Selector(response)
        if node.value.args:
            param = node.value.args[0]
            if self.is_response(param):
                yield Issue(
                    code=4,
                    summary="use response.selector or response.xpath or response.css instead",
                    line=node.lineno,
                    column=node.col_offset,
                )
                return

        # look for: Selector(response=response) or Selector(text=response.text)
        for kw in node.value.keywords:
            if self.has_response_for_keyword_parameter(kw):
                yield Issue(
                    code=4,
                    summary="use response.selector or response.xpath or response.css instead",
                    line=node.lineno,
                    column=node.col_offset,
                )
                return
