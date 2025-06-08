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


class NonFrozenDependenciesIssueFinder(IssueFinder):
    msg_code = "SCP12"
    msg_info = "non-frozen dependency in requirements.txt"

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

    def is_frozen_dependency(self, line):
        """Check if a dependency line is frozen (has exact version specification)."""
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("#"):
            return True

        # Skip lines with -r, -e, or other pip options
        if line.startswith("-"):
            return True

        # Check for exact version pinning (==)
        if "==" in line:
            return True

        # Allow git+https URLs and other URL specifications
        if line.startswith(
            ("git+", "hg+", "svn+", "bzr+", "http://", "https://", "file://")
        ):
            return True

        # Allow local file paths
        return line.startswith((".", "/"))

    def find_issues(self, node) -> Generator[tuple[int, int, str], None, None]:
        if not self.filename:
            return

        project_root = self.get_project_root(self.filename)
        if not project_root:
            return

        # Only check each project once
        project_key = str(project_root)
        if project_key in self._checked_projects:
            return

        self._checked_projects.add(project_key)

        requirements_txt = project_root / "requirements.txt"
        if not requirements_txt.exists():
            return

        try:
            content = requirements_txt.read_text(encoding="utf-8")
            lines = content.splitlines()

            for line_num, line in enumerate(lines, 1):
                if not self.is_frozen_dependency(line):
                    # Extract package name for better error message
                    package_name = (
                        line.strip()
                        .split()[0]
                        .split(">=")[0]
                        .split(">")[0]
                        .split("<=")[0]
                        .split("<")[0]
                        .split("!=")[0]
                        .split("~=")[0]
                    )
                    message = f"{self.msg_code} {self.msg_info}: {package_name}"
                    yield (line_num, 0, message)

        except (OSError, UnicodeDecodeError):
            # If we can't read the file, skip the check
            return
