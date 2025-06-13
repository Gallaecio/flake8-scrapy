from ast import Assign, Constant, Module, Name, NodeVisitor

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
        seen: dict[str, int] = {}  # setting name: line number
        autothrottle_enabled = False
        for child in node.body:
            if not isinstance(child, Assign):
                continue
            for target in child.targets:
                if not (isinstance(target, Name) and target.id.isupper()):
                    continue
                name = target.id
                if name in seen:
                    self.issues.append(
                        Issue(
                            23,
                            "redefined setting",
                            detail=f"seen first at line {seen[name]}",
                            line=child.lineno,
                            column=child.col_offset,
                        )
                    )
                    continue
                seen[name] = child.lineno
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
                if name == "ROBOTSTXT_OBEY" and isinstance(child.value, Constant):
                    try:
                        value = getbool(child.value.value)
                    except ValueError:
                        pass
                    else:
                        if value is False:
                            self.issues.append(
                                Issue(
                                    20,
                                    "ROBOTSTXT_OBEY not enabled",
                                    line=child.lineno,
                                    column=child.value.col_offset,
                                )
                            )
        if "USER_AGENT" not in seen:
            self.issues.append(Issue(19, "no USER_AGENT"))
        if "ROBOTSTXT_OBEY" not in seen:
            self.issues.append(Issue(20, "ROBOTSTXT_OBEY not enabled"))
        if not autothrottle_enabled and not all(
            setting in seen
            for setting in (
                "CONCURRENT_REQUESTS",
                "CONCURRENT_REQUESTS_PER_DOMAIN",
                "DOWNLOAD_DELAY",
            )
        ):
            self.issues.append(Issue(21, "incomplete throttling config"))
