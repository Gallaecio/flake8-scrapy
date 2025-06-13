import ast
from ast import Assign, Constant, Module, Name, NodeVisitor
from contextlib import suppress

from flake8_scrapy._finders.data import getbool
from flake8_scrapy._finders.messaging import Issue


class SettingsModuleIssueFinder(NodeVisitor):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.issues = []

    def visit_Module(self, node: Module) -> None:  # noqa: PLR0912,PLR0915
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
                elif name == "ROBOTSTXT_OBEY":
                    value = True
                    col_offset = child.col_offset
                    if isinstance(child.value, Constant):
                        col_offset = child.value.col_offset
                        with suppress(ValueError):
                            value = getbool(child.value.value)
                    robotstxt_obey_values.append((value, child.lineno, col_offset))
                elif name not in self.config.known_settings:
                    detail = None
                    if suggestions := self.config.get_setting_suggestions(name):
                        if len(suggestions) == 1:
                            detail = f"Did you mean {suggestions[0]}?"
                        else:
                            suggestion_list = ", ".join(suggestions)
                            detail = f"Did you mean one of: {suggestion_list}?"
                    self.issues.append(
                        Issue(
                            7,
                            "unknown setting",
                            detail=detail,
                            line=child.lineno,
                            column=child.col_offset,
                        )
                    )
                elif name in self.config.deprecated_settings:
                    self.issues.append(
                        Issue(
                            8,
                            "deprecated setting",
                            line=child.lineno,
                            column=child.col_offset,
                        )
                    )
                # elif issue := get_setting_value_issue(name, child.value):
                #     self.issues.append(issue)

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
