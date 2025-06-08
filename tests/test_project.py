import tempfile
from pathlib import Path

from flake8_scrapy._finders.project import RequirementsTxtIssueFinder

from . import run_checker


def test_missing_requirements_txt():
    code = "import scrapy\n\nclass TestSpider(scrapy.Spider):\n    name = 'test'\n"

    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "spider.py"
        test_file.write_text(code)
        issues = run_checker(code, filename=str(test_file), enable_project_checks=True)
        scp11_issues = [issue for issue in issues if "SCP11" in issue[2]]
        assert len(scp11_issues) == 1
        assert scp11_issues[0][0] == 1  # line
        assert scp11_issues[0][1] == 0  # col
        assert RequirementsTxtIssueFinder.msg_code in scp11_issues[0][2]
        assert RequirementsTxtIssueFinder.msg_info in scp11_issues[0][2]


def test_requirements_txt_exists():
    code = "import scrapy\n\nclass TestSpider(scrapy.Spider):\n    name = 'test'\n"

    with tempfile.TemporaryDirectory() as temp_dir:
        requirements_file = Path(temp_dir) / "requirements.txt"
        requirements_file.write_text("scrapy==2.13.1\n")
        test_file = Path(temp_dir) / "spider.py"
        test_file.write_text(code)
        issues = run_checker(code, filename=str(test_file), enable_project_checks=True)
        scp11_issues = [issue for issue in issues if "SCP11" in issue[2]]
        assert len(scp11_issues) == 0


def test_requirements_txt_in_parent_directory():
    code = "import scrapy\n\nclass TestSpider(scrapy.Spider):\n    name = 'test'\n"

    with tempfile.TemporaryDirectory() as temp_dir:
        requirements_file = Path(temp_dir) / "requirements.txt"
        requirements_file.write_text("scrapy==2.13.1\n")
        subdir = Path(temp_dir) / "spiders"
        subdir.mkdir()
        test_file = subdir / "spider.py"
        test_file.write_text(code)
        issues = run_checker(code, filename=str(test_file), enable_project_checks=True)
        scp11_issues = [issue for issue in issues if "SCP11" in issue[2]]
        assert len(scp11_issues) == 0


def test_no_duplicate_reports():
    code = "import scrapy\n\nclass TestSpider(scrapy.Spider):\n    name = 'test'\n"

    with tempfile.TemporaryDirectory() as temp_dir:
        test_file1 = Path(temp_dir) / "spider1.py"
        test_file1.write_text(code)
        test_file2 = Path(temp_dir) / "spider2.py"
        test_file2.write_text(code)
        issues1 = run_checker(
            code, filename=str(test_file1), enable_project_checks=True
        )
        scp11_issues1 = [issue for issue in issues1 if "SCP11" in issue[2]]
        issues2 = run_checker(
            code, filename=str(test_file2), enable_project_checks=True
        )
        scp11_issues2 = [issue for issue in issues2 if "SCP11" in issue[2]]
        assert len(scp11_issues1) == 1
        assert len(scp11_issues2) == 1
