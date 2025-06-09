import tempfile
from pathlib import Path

from flake8_scrapy._finders.project import (
    AncientScrapyVersionIssueFinder,
    InsecureScrapyVersionIssueFinder,
    NonFrozenDependenciesIssueFinder,
    RequirementsTxtIssueFinder,
)

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


def test_non_frozen_dependencies():
    code = "import scrapy\n\nclass TestSpider(scrapy.Spider):\n    name = 'test'\n"
    with tempfile.TemporaryDirectory() as temp_dir:
        requirements_file = Path(temp_dir) / "requirements.txt"
        requirements_file.write_text(
            "scrapy>=2.0\nrequests\nbeautifulsoup4~=4.9\nlxml==4.6.3\n"
        )
        test_file = Path(temp_dir) / "spider.py"
        test_file.write_text(code)
        issues = run_checker(code, filename=str(test_file), enable_project_checks=True)
        scp12_issues = [issue for issue in issues if "SCP12" in issue[2]]
        assert len(scp12_issues) == 3

        # Check first issue (scrapy>=2.0)
        assert scp12_issues[0][0] == 1  # line
        assert scp12_issues[0][1] == 0  # col
        assert NonFrozenDependenciesIssueFinder.msg_code in scp12_issues[0][2]
        assert "scrapy" in scp12_issues[0][2]

        # Check second issue (requests)
        assert scp12_issues[1][0] == 2  # line
        assert "requests" in scp12_issues[1][2]

        # Check third issue (beautifulsoup4~=4.9)
        assert scp12_issues[2][0] == 3  # line
        assert "beautifulsoup4" in scp12_issues[2][2]


def test_all_frozen_dependencies():
    code = "import scrapy\n\nclass TestSpider(scrapy.Spider):\n    name = 'test'\n"
    with tempfile.TemporaryDirectory() as temp_dir:
        requirements_file = Path(temp_dir) / "requirements.txt"
        requirements_file.write_text(
            "scrapy==2.13.1\nrequests==2.28.0\nbeautifulsoup4==4.11.1\nlxml==4.6.3\n"
        )
        test_file = Path(temp_dir) / "spider.py"
        test_file.write_text(code)
        issues = run_checker(code, filename=str(test_file), enable_project_checks=True)
        scp12_issues = [issue for issue in issues if "SCP12" in issue[2]]
        assert len(scp12_issues) == 0


def test_requirements_with_comments_and_options():
    code = "import scrapy\n\nclass TestSpider(scrapy.Spider):\n    name = 'test'\n"
    with tempfile.TemporaryDirectory() as temp_dir:
        requirements_file = Path(temp_dir) / "requirements.txt"
        requirements_file.write_text(
            "# This is a comment\n"
            "scrapy==2.13.1\n"
            "-r requirements-dev.txt\n"
            "requests  # Another comment\n"
            "-e git+https://github.com/user/repo.git#egg=package\n"
            "https://github.com/user/package/archive/main.zip\n"
            "\n"
            "beautifulsoup4>=4.9\n"
        )
        test_file = Path(temp_dir) / "spider.py"
        test_file.write_text(code)
        issues = run_checker(code, filename=str(test_file), enable_project_checks=True)
        scp12_issues = [issue for issue in issues if "SCP12" in issue[2]]

        # Should find 2 non-frozen dependencies (requests, beautifulsoup4)
        assert len(scp12_issues) == 2
        assert scp12_issues[0][0] == 4  # requests line
        assert "requests" in scp12_issues[0][2]
        assert scp12_issues[1][0] == 8  # beautifulsoup4 line
        assert "beautifulsoup4" in scp12_issues[1][2]


def test_no_requirements_txt_no_scp12():
    code = "import scrapy\n\nclass TestSpider(scrapy.Spider):\n    name = 'test'\n"
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "spider.py"
        test_file.write_text(code)
        issues = run_checker(code, filename=str(test_file), enable_project_checks=True)
        scp12_issues = [issue for issue in issues if "SCP12" in issue[2]]
        assert len(scp12_issues) == 0


def test_ancient_scrapy_version():
    code = "import scrapy\n\nclass TestSpider(scrapy.Spider):\n    name = 'test'\n"
    with tempfile.TemporaryDirectory() as temp_dir:
        requirements_file = Path(temp_dir) / "requirements.txt"
        requirements_file.write_text("scrapy==1.8.0\nrequests==2.28.0\n")
        test_file = Path(temp_dir) / "spider.py"
        test_file.write_text(code)
        issues = run_checker(code, filename=str(test_file), enable_project_checks=True)
        scp13_issues = [issue for issue in issues if "SCP13" in issue[2]]
        assert len(scp13_issues) == 1
        assert scp13_issues[0][0] == 1  # line
        assert scp13_issues[0][1] == 0  # col
        assert AncientScrapyVersionIssueFinder.msg_code in scp13_issues[0][2]
        assert "1.8.0" in scp13_issues[0][2]
        assert "minimum required: 2.0.1" in scp13_issues[0][2]


def test_current_scrapy_version():
    code = "import scrapy\n\nclass TestSpider(scrapy.Spider):\n    name = 'test'\n"
    with tempfile.TemporaryDirectory() as temp_dir:
        requirements_file = Path(temp_dir) / "requirements.txt"
        requirements_file.write_text("scrapy==2.13.1\nrequests==2.28.0\n")
        test_file = Path(temp_dir) / "spider.py"
        test_file.write_text(code)
        issues = run_checker(code, filename=str(test_file), enable_project_checks=True)
        scp13_issues = [issue for issue in issues if "SCP13" in issue[2]]
        assert len(scp13_issues) == 0


def test_edge_case_scrapy_versions():
    code = "import scrapy\n\nclass TestSpider(scrapy.Spider):\n    name = 'test'\n"
    with tempfile.TemporaryDirectory() as temp_dir:
        requirements_file = Path(temp_dir) / "requirements.txt"
        requirements_file.write_text("scrapy==2.0.0\nscrapy==2.0.1\nscrapy==2.1.0\n")
        test_file = Path(temp_dir) / "spider.py"
        test_file.write_text(code)
        issues = run_checker(code, filename=str(test_file), enable_project_checks=True)
        scp13_issues = [issue for issue in issues if "SCP13" in issue[2]]
        assert len(scp13_issues) == 1
        assert scp13_issues[0][0] == 1  # first line
        assert "2.0.0" in scp13_issues[0][2]


def test_non_frozen_scrapy_no_scp13():
    code = "import scrapy\n\nclass TestSpider(scrapy.Spider):\n    name = 'test'\n"
    with tempfile.TemporaryDirectory() as temp_dir:
        requirements_file = Path(temp_dir) / "requirements.txt"
        requirements_file.write_text("scrapy>=1.8.0\nscrapy\n")
        test_file = Path(temp_dir) / "spider.py"
        test_file.write_text(code)
        issues = run_checker(code, filename=str(test_file), enable_project_checks=True)
        scp13_issues = [issue for issue in issues if "SCP13" in issue[2]]
        assert len(scp13_issues) == 0


def test_scrapy_with_comments_scp13():
    code = "import scrapy\n\nclass TestSpider(scrapy.Spider):\n    name = 'test'\n"
    with tempfile.TemporaryDirectory() as temp_dir:
        requirements_file = Path(temp_dir) / "requirements.txt"
        requirements_file.write_text(
            "# Core dependencies\n"
            "scrapy==1.5.0  # This is an old version\n"
            "requests==2.28.0\n"
        )
        test_file = Path(temp_dir) / "spider.py"
        test_file.write_text(code)
        issues = run_checker(code, filename=str(test_file), enable_project_checks=True)
        scp13_issues = [issue for issue in issues if "SCP13" in issue[2]]
        assert len(scp13_issues) == 1
        assert scp13_issues[0][0] == 2  # second line
        assert "1.5.0" in scp13_issues[0][2]


def test_no_scrapy_dependency_no_scp13():
    code = "import scrapy\n\nclass TestSpider(scrapy.Spider):\n    name = 'test'\n"
    with tempfile.TemporaryDirectory() as temp_dir:
        requirements_file = Path(temp_dir) / "requirements.txt"
        requirements_file.write_text("requests==2.28.0\nbeautifulsoup4==4.11.1\n")
        test_file = Path(temp_dir) / "spider.py"
        test_file.write_text(code)
        issues = run_checker(code, filename=str(test_file), enable_project_checks=True)
        scp13_issues = [issue for issue in issues if "SCP13" in issue[2]]
        assert len(scp13_issues) == 0


def test_scrapy_prerelease_versions():
    """Test that SCP13 handles pre-release versions correctly"""
    code = "import scrapy\n\nclass TestSpider(scrapy.Spider):\n    name = 'test'\n"
    with tempfile.TemporaryDirectory() as temp_dir:
        requirements_file = Path(temp_dir) / "requirements.txt"
        requirements_file.write_text(
            "scrapy==2.0.2a2\nscrapy==2.0.1rc1\nscrapy==2.0.0a1\nscrapy==1.8.0.post1\n"
        )
        test_file = Path(temp_dir) / "spider.py"
        test_file.write_text(code)
        issues = run_checker(code, filename=str(test_file), enable_project_checks=True)
        scp13_issues = [issue for issue in issues if "SCP13" in issue[2]]
        assert len(scp13_issues) == 3
        assert scp13_issues[0][0] == 2  # 2.0.1rc1 line
        assert "2.0.1rc1" in scp13_issues[0][2]
        assert scp13_issues[1][0] == 3  # 2.0.0a1 line
        assert "2.0.0a1" in scp13_issues[1][2]
        assert scp13_issues[2][0] == 4  # 1.8.0.post1 line
        assert "1.8.0.post1" in scp13_issues[2][2]


def test_insecure_scrapy_version():
    code = "import scrapy\n\nclass TestSpider(scrapy.Spider):\n    name = 'test'\n"
    with tempfile.TemporaryDirectory() as temp_dir:
        requirements_file = Path(temp_dir) / "requirements.txt"
        requirements_file.write_text("scrapy==2.10.0\n")
        test_file = Path(temp_dir) / "spider.py"
        test_file.write_text(code)
        issues = run_checker(code, filename=str(test_file), enable_project_checks=True)
        scp14_issues = [issue for issue in issues if "SCP14" in issue[2]]
        assert len(scp14_issues) == 1
        assert scp14_issues[0][0] == 1  # line
        assert scp14_issues[0][1] == 0  # col
        assert InsecureScrapyVersionIssueFinder.msg_code in scp14_issues[0][2]
        assert "2.10.0" in scp14_issues[0][2]
        assert "minimum required: 2.11.2" in scp14_issues[0][2]


def test_secure_scrapy_version():
    code = "import scrapy\n\nclass TestSpider(scrapy.Spider):\n    name = 'test'\n"
    with tempfile.TemporaryDirectory() as temp_dir:
        requirements_file = Path(temp_dir) / "requirements.txt"
        requirements_file.write_text("scrapy==2.11.2\n")
        test_file = Path(temp_dir) / "spider.py"
        test_file.write_text(code)
        issues = run_checker(code, filename=str(test_file), enable_project_checks=True)
        scp14_issues = [issue for issue in issues if "SCP14" in issue[2]]
        assert len(scp14_issues) == 0


def test_edge_case_scrapy_security_versions():
    code = "import scrapy\n\nclass TestSpider(scrapy.Spider):\n    name = 'test'\n"
    with tempfile.TemporaryDirectory() as temp_dir:
        requirements_file = Path(temp_dir) / "requirements.txt"
        requirements_file.write_text("scrapy==2.11.1\nscrapy==2.11.2\nscrapy==2.12.0\n")
        test_file = Path(temp_dir) / "spider.py"
        test_file.write_text(code)
        issues = run_checker(code, filename=str(test_file), enable_project_checks=True)
        scp14_issues = [issue for issue in issues if "SCP14" in issue[2]]
        assert len(scp14_issues) == 1
        assert scp14_issues[0][0] == 1  # first line
        assert "2.11.1" in scp14_issues[0][2]


def test_non_frozen_scrapy_no_scp14():
    code = "import scrapy\n\nclass TestSpider(scrapy.Spider):\n    name = 'test'\n"
    with tempfile.TemporaryDirectory() as temp_dir:
        requirements_file = Path(temp_dir) / "requirements.txt"
        requirements_file.write_text("scrapy>=2.10.0\nscrapy\nrequests==2.28.0\n")
        test_file = Path(temp_dir) / "spider.py"
        test_file.write_text(code)
        issues = run_checker(code, filename=str(test_file), enable_project_checks=True)
        scp14_issues = [issue for issue in issues if "SCP14" in issue[2]]
        assert len(scp14_issues) == 0


def test_scrapy_with_comments_scp14():
    code = "import scrapy\n\nclass TestSpider(scrapy.Spider):\n    name = 'test'\n"
    with tempfile.TemporaryDirectory() as temp_dir:
        requirements_file = Path(temp_dir) / "requirements.txt"
        requirements_file.write_text(
            "# Core dependencies\nscrapy==2.9.0  # This version has security issues\n"
        )
        test_file = Path(temp_dir) / "spider.py"
        test_file.write_text(code)
        issues = run_checker(code, filename=str(test_file), enable_project_checks=True)
        scp14_issues = [issue for issue in issues if "SCP14" in issue[2]]
        assert len(scp14_issues) == 1
        assert scp14_issues[0][0] == 2  # second line
        assert "2.9.0" in scp14_issues[0][2]


def test_no_scrapy_dependency_no_scp14():
    code = "import scrapy\n\nclass TestSpider(scrapy.Spider):\n    name = 'test'\n"
    with tempfile.TemporaryDirectory() as temp_dir:
        requirements_file = Path(temp_dir) / "requirements.txt"
        requirements_file.write_text("requests==2.28.0\nbeautifulsoup4==4.11.1\n")
        test_file = Path(temp_dir) / "spider.py"
        test_file.write_text(code)
        issues = run_checker(code, filename=str(test_file), enable_project_checks=True)
        scp14_issues = [issue for issue in issues if "SCP14" in issue[2]]
        assert len(scp14_issues) == 0


def test_multiple_scrapy_version_checks():
    code = "import scrapy\n\nclass TestSpider(scrapy.Spider):\n    name = 'test'\n"
    with tempfile.TemporaryDirectory() as temp_dir:
        requirements_file = Path(temp_dir) / "requirements.txt"
        requirements_file.write_text(
            "scrapy==1.8.0\n"  # Ancient (triggers both SCP13 and SCP14)
            "scrapy==2.5.0\n"  # Only insecure (triggers only SCP14)
        )
        test_file = Path(temp_dir) / "spider.py"
        test_file.write_text(code)
        issues = run_checker(code, filename=str(test_file), enable_project_checks=True)
        scp13_issues = [issue for issue in issues if "SCP13" in issue[2]]
        scp14_issues = [issue for issue in issues if "SCP14" in issue[2]]

        # Should find 1 ancient version (1.8.0)
        assert len(scp13_issues) == 1
        assert "1.8.0" in scp13_issues[0][2]

        # Should find 2 insecure versions (1.8.0 and 2.5.0)
        assert len(scp14_issues) == 2
        assert "1.8.0" in scp14_issues[0][2]
        assert "2.5.0" in scp14_issues[1][2]


def test_obsolete_packages_scrapy_crawlera():
    code = "import scrapy\n\nclass TestSpider(scrapy.Spider):\n    name = 'test'\n"
    with tempfile.TemporaryDirectory() as temp_dir:
        requirements_file = Path(temp_dir) / "requirements.txt"
        requirements_file.write_text("scrapy-crawlera==1.7.0\nscrapy==2.11.0\n")
        test_file = Path(temp_dir) / "spider.py"
        test_file.write_text(code)
        issues = run_checker(code, filename=str(test_file), enable_project_checks=True)
        scp16_issues = [issue for issue in issues if "SCP16" in issue[2]]

        assert len(scp16_issues) == 1
        assert "scrapy-crawlera" in scp16_issues[0][2]
        assert "scrapy-zyte-smartproxy" in scp16_issues[0][2]
        assert "use scrapy-zyte-smartproxy instead" in scp16_issues[0][2]


def test_obsolete_packages_scrapy_splash():
    code = "import scrapy\n\nclass TestSpider(scrapy.Spider):\n    name = 'test'\n"
    with tempfile.TemporaryDirectory() as temp_dir:
        requirements_file = Path(temp_dir) / "requirements.txt"
        requirements_file.write_text("scrapy-splash==0.8.0\nscrapy==2.11.0\n")
        test_file = Path(temp_dir) / "spider.py"
        test_file.write_text(code)
        issues = run_checker(code, filename=str(test_file), enable_project_checks=True)
        scp16_issues = [issue for issue in issues if "SCP16" in issue[2]]

        assert len(scp16_issues) == 1
        assert "scrapy-splash" in scp16_issues[0][2]
        assert "scrapy-zyte-api or scrapy-playwright" in scp16_issues[0][2]
        assert "use scrapy-zyte-api or scrapy-playwright instead" in scp16_issues[0][2]


def test_obsolete_packages_multiple():
    code = "import scrapy\n\nclass TestSpider(scrapy.Spider):\n    name = 'test'\n"
    with tempfile.TemporaryDirectory() as temp_dir:
        requirements_file = Path(temp_dir) / "requirements.txt"
        requirements_file.write_text(
            "scrapy-crawlera==1.7.0\nscrapy-splash==0.8.0\nscrapy==2.11.0\n"
        )
        test_file = Path(temp_dir) / "spider.py"
        test_file.write_text(code)
        issues = run_checker(code, filename=str(test_file), enable_project_checks=True)
        scp16_issues = [issue for issue in issues if "SCP16" in issue[2]]

        assert len(scp16_issues) == 2
        crawlera_issues = [
            issue for issue in scp16_issues if "scrapy-crawlera" in issue[2]
        ]
        splash_issues = [issue for issue in scp16_issues if "scrapy-splash" in issue[2]]

        assert len(crawlera_issues) == 1
        assert len(splash_issues) == 1


def test_obsolete_packages_non_frozen():
    code = "import scrapy\n\nclass TestSpider(scrapy.Spider):\n    name = 'test'\n"
    with tempfile.TemporaryDirectory() as temp_dir:
        requirements_file = Path(temp_dir) / "requirements.txt"
        requirements_file.write_text("scrapy-crawlera\nscrapy==2.11.0\n")
        test_file = Path(temp_dir) / "spider.py"
        test_file.write_text(code)
        issues = run_checker(code, filename=str(test_file), enable_project_checks=True)
        scp16_issues = [issue for issue in issues if "SCP16" in issue[2]]

        assert len(scp16_issues) == 1
        assert "scrapy-crawlera" in scp16_issues[0][2]


def test_no_obsolete_packages():
    code = "import scrapy\n\nclass TestSpider(scrapy.Spider):\n    name = 'test'\n"
    with tempfile.TemporaryDirectory() as temp_dir:
        requirements_file = Path(temp_dir) / "requirements.txt"
        requirements_file.write_text(
            "scrapy==2.11.0\nscrapy-zyte-smartproxy==3.0.0\nscrapy-playwright==0.0.26\n"
        )
        test_file = Path(temp_dir) / "spider.py"
        test_file.write_text(code)
        issues = run_checker(code, filename=str(test_file), enable_project_checks=True)
        scp16_issues = [issue for issue in issues if "SCP16" in issue[2]]

        assert len(scp16_issues) == 0


def test_project_finder_without_filename():
    code = "import scrapy\n\nclass TestSpider(scrapy.Spider):\n    name = 'test'\n"
    issues = run_checker(code, filename=None, enable_project_checks=True)
    project_issues = [
        issue
        for issue in issues
        if any(f"SCP{i}" in issue[2] for i in [11, 12, 13, 14, 16])
    ]
    assert len(project_issues) == 0


def test_unreadable_requirements_txt():
    import stat

    code = "import scrapy\n\nclass TestSpider(scrapy.Spider):\n    name = 'test'\n"
    with tempfile.TemporaryDirectory() as temp_dir:
        requirements_file = Path(temp_dir) / "requirements.txt"
        requirements_file.write_text("scrapy==2.11.0\n")

        # Remove read permissions
        original_mode = requirements_file.stat().st_mode
        requirements_file.chmod(stat.S_IWRITE)

        test_file = Path(temp_dir) / "spider.py"
        test_file.write_text(code)

        try:
            issues = run_checker(
                code, filename=str(test_file), enable_project_checks=True
            )
            project_issues = [
                issue
                for issue in issues
                if any(f"SCP{i}" in issue[2] for i in [11, 12, 13, 14, 16])
            ]
            assert len(project_issues) == 0
        finally:
            # Restore permissions for cleanup
            requirements_file.chmod(original_mode)


def test_invalid_version_format():
    from flake8_scrapy._finders.utilities import is_version_less_than

    result = is_version_less_than("invalid-version", "2.0.0")
    assert result is False

    result = is_version_less_than("invalid-version", "2.11.2")
    assert result is False
