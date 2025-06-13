import ast
from ast import Assign, Constant, Module, Name, NodeVisitor
from contextlib import suppress

from flake8_scrapy._finders.data import getbool
from flake8_scrapy._finders.messaging import Issue


class SettingsModuleIssueFinder(NodeVisitor):
    def __init__(
        self,
        filename=None,
        allowed_settings=None,
    ):
        super().__init__()
        self.issues = []

    def visit_Module(self, node: Module) -> None:  # noqa: PLR0912
        # setting name: line number
        top_level_seen: dict[str, int] = {}
        all_seen: set[str] = set()

        autothrottle_enabled = False
        robotstxt_obey_values = []

        # First pass: check for redefinitions at top level only
        for child in node.body:
            if not isinstance(child, Assign):
                continue
            for target in child.targets:
                if not (isinstance(target, Name) and target.id.isupper()):
                    continue
                name = target.id
                if name in top_level_seen:
                    self.issues.append(
                        Issue(
                            23,
                            "redefined setting",
                            detail=f"seen first at line {top_level_seen[name]}",
                            line=child.lineno,
                            column=child.col_offset,
                        )
                    )
                    continue
                top_level_seen[name] = child.lineno

        # Second pass: collect all settings and check specific values
        for child in ast.walk(node):
            if not isinstance(child, Assign):
                continue
            for target in child.targets:
                if not (isinstance(target, Name) and target.id.isupper()):
                    continue
                name = target.id
                all_seen.add(name)
                if name == "AUTOTHROTTLE_ENABLED":
                    if not isinstance(child.value, Constant):
                        autothrottle_enabled = True
                    else:
                        try:
                            value = getbool(child.value.value)
                        except ValueError:
                            autothrottle_enabled = True
                        else:
                            autothrottle_enabled = value
                if name == "ROBOTSTXT_OBEY":
                    value = True
                    if isinstance(child.value, Constant):
                        with suppress(ValueError):
                            value = getbool(child.value.value)
                    robotstxt_obey_values.append(
                        (value, child.lineno, child.col_offset)
                    )

        if "USER_AGENT" not in all_seen:
            self.issues.append(Issue(19, "no USER_AGENT"))

        if not robotstxt_obey_values:
            self.issues.append(Issue(20, "ROBOTSTXT_OBEY not enabled"))
        elif all(not value for value, _, _ in robotstxt_obey_values):
            _, line, col = robotstxt_obey_values[0]
            self.issues.append(
                Issue(20, "ROBOTSTXT_OBEY not enabled", line=line, column=col)
            )

        if not autothrottle_enabled and not all(
            setting in all_seen
            for setting in (
                "CONCURRENT_REQUESTS",
                "CONCURRENT_REQUESTS_PER_DOMAIN",
                "DOWNLOAD_DELAY",
            )
        ):
            self.issues.append(Issue(21, "incomplete throttling config"))
