from collections.abc import Generator
from pathlib import Path

from . import IssueFinder


class RequirementsTxtIssueFinder(IssueFinder):
    msg_code = "SCP11"
    msg_info = "missing requirements.txt"

    def __init__(self, filename=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filename = filename
        self._checked_projects = set()

    def get_project_root(self, filepath):
        if not filepath:
            return None
        path = Path(filepath).resolve()
        for parent in [path, *list(path.parents)]:
            indicators = [
                "scrapy.cfg",
                "pyproject.toml",
                "setup.py",
                "setup.cfg",
                ".git",
                "scrapinghub.yml",
                "requirements.txt",
            ]
            if any((parent / indicator).exists() for indicator in indicators):
                return parent
        # If no indicators are found, use the directory containing the file
        return path.parent if path.is_file() else path

    def find_issues(self, node) -> Generator[tuple[int, int, str], None, None]:
        if not self.filename:
            return
        project_root = self.get_project_root(self.filename)
        if not project_root:
            return
        project_key = str(project_root)
        if project_key in self._checked_projects:
            return
        self._checked_projects.add(project_key)
        requirements_txt = project_root / "requirements.txt"
        if not requirements_txt.exists():
            yield (1, 0, self.message)
