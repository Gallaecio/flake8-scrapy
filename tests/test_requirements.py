from packaging.utils import canonicalize_name

from flake8_scrapy.finders.requirements import RequirementsIssueFinder

from . import NO_ISSUE, File, Issue, cases
from .helpers import check_project

CASES = (
    # No scrapy.cfg file
    ((File("", path="requirements.txt"),), NO_ISSUE),
    # Different requirements file name - should not trigger
    ((File("", path="scrapy.cfg"), File("", path="requirements-dev.txt")), NO_ISSUE),
    # Content-based test cases
    *(
        ((File("", path="scrapy.cfg"), File(requirements, path=path)), issues)
        for path in ("requirements.txt",)
        for requirements, issues in (
            *(
                (requirements, NO_ISSUE)
                for requirements in (
                    # All required dependencies with standard package names
                    "\n".join(
                        [
                            "scrapy==2.11.0",
                            "cryptography==41.0.4",
                            "cssselect==1.2.0",
                            "lxml==4.9.3",
                            "parsel==1.8.1",
                            "protego==0.3.0",
                            "pyOpenSSL==23.2.0",
                            "queuelib==1.7.0",
                            "service-identity==23.1.0",
                            "Twisted==23.8.0",
                            "w3lib==2.1.2",
                            "zope.interface==6.0",
                        ]
                    ),
                    # Different package name formats (service_identity vs
                    # service-identity, twisted vs Twisted)
                    "\n".join(
                        [
                            "scrapy==2.11.0",
                            "cryptography==41.0.4",
                            "cssselect==1.2.0",
                            "lxml==4.9.3",
                            "parsel==1.8.1",
                            "protego==0.3.0",
                            "pyOpenSSL==23.2.0",
                            "queuelib==1.7.0",
                            "service_identity==23.1.0",
                            "twisted==23.8.0",
                            "w3lib==2.1.2",
                            "zope.interface==6.0",
                        ]
                    ),
                    # All required dependencies plus extra packages
                    "\n".join(
                        [
                            "scrapy==2.11.0",
                            "requests==2.31.0",
                            "cryptography==41.0.4",
                            "cssselect==1.2.0",
                            "lxml==4.9.3",
                            "parsel==1.8.1",
                            "protego==0.3.0",
                            "pyOpenSSL==23.2.0",
                            "queuelib==1.7.0",
                            "service-identity==23.1.0",
                            "Twisted==23.8.0",
                            "w3lib==2.1.2",
                            "zope.interface==6.0",
                            "boto3==1.28.85",
                        ]
                    ),
                )
            ),
            *(
                (requirements, Issue("SCP13 incomplete requirements freeze", path=path))
                for requirements in (
                    # Empty requirements file
                    "",
                    # Only comments in requirements file
                    "\n".join(["# This is a comment", "# Another comment"]),
                    # Editable install (not frozen)
                    "-e git+https://github.com/scrapy/scrapy.git#egg=scrapy",
                    # Missing most required dependencies
                    "\n".join(["scrapy==2.11.0", "requests==2.31.0"]),
                    # Missing some required dependencies
                    "\n".join(
                        [
                            "scrapy==2.11.0",
                            "cryptography==41.0.4",
                            "cssselect==1.2.0",
                            "lxml==4.9.3",
                            "parsel==1.8.1",
                        ]
                    ),
                )
            ),
        )
    ),
)


@cases(CASES)
def test(input, expected):
    check_project(input, expected)


def test_required_dependencies_are_canonical():
    for dep in RequirementsIssueFinder.REQUIRED_DEPENDENCIES:
        assert dep == canonicalize_name(dep)
