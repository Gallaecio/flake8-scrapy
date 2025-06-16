from packaging.utils import canonicalize_name
from packaging.version import Version

from flake8_scrapy.data.packages import PACKAGES
from flake8_scrapy.finders.requirements import RequirementsIssueFinder

from . import NO_ISSUE, File, Issue, cases
from .helpers import check_project

SCRAPY_FUTURE_VERSION = Version("3.0.0")
SCRAPY_HIGHEST_KNOWN = PACKAGES["scrapy"].highest_known_version
SCRAPY_LOWEST_SAFE = PACKAGES["scrapy"].lowest_safe_version
SCRAPY_INSECURE_VERSION = Version("2.11.1")
SCRAPY_LOWEST_SUPPORTED = PACKAGES["scrapy"].lowest_supported_version
SCRAPY_ANCIENT_VERSION = Version("2.0.0")

CASES = (
    # No scrapy.cfg file
    ((File("", path="requirements.txt"),), NO_ISSUE),
    # Non-standard requirements file name
    ((File("", path="scrapy.cfg"), File("", path="requirements-dev.txt")), NO_ISSUE),
    # SCP13 incomplete requirement freeze
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
                            f"scrapy=={SCRAPY_HIGHEST_KNOWN}",
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
                            f"scrapy=={SCRAPY_HIGHEST_KNOWN}",
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
                            f"scrapy=={SCRAPY_HIGHEST_KNOWN}",
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
                    "\n".join([f"scrapy=={SCRAPY_HIGHEST_KNOWN}", "requests==2.31.0"]),
                    # Missing some required dependencies
                    "\n".join(
                        [
                            f"scrapy=={SCRAPY_HIGHEST_KNOWN}",
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
    # Tests for specific requirements
    *(
        (
            (File("", path="scrapy.cfg"), File(requirements, path=path)),
            (Issue("SCP13 incomplete requirements freeze", path=path), *issues),
        )
        for path in ("requirements.txt",)
        for requirements, issues in (
            # SCP14 unsupported requirement
            # SCP15 insecure requirement
            *(
                (f"scrapy=={version}", issues)
                for version, issues in (
                    (SCRAPY_FUTURE_VERSION, ()),
                    (SCRAPY_HIGHEST_KNOWN, ()),
                    (SCRAPY_LOWEST_SAFE, ()),
                    (
                        SCRAPY_INSECURE_VERSION,
                        (
                            Issue(
                                f"SCP15 insecure requirement: scrapy {SCRAPY_LOWEST_SAFE} implements security fixes",
                                path=path,
                            ),
                        ),
                    ),
                    (
                        SCRAPY_LOWEST_SUPPORTED,
                        (
                            Issue(
                                f"SCP15 insecure requirement: scrapy {SCRAPY_LOWEST_SAFE} implements security fixes",
                                path=path,
                            ),
                        ),
                    ),
                    (
                        SCRAPY_ANCIENT_VERSION,
                        (
                            Issue(
                                f"SCP14 unsupported requirement: scrapy-flake8 only supports scrapy>={SCRAPY_LOWEST_SUPPORTED}+",
                                path=path,
                            ),
                            Issue(
                                f"SCP15 insecure requirement: scrapy {SCRAPY_LOWEST_SAFE} implements security fixes",
                                path=path,
                            ),
                        ),
                    ),
                )
            ),
            # Non-frozen versions should not trigger SCP14/SCP15
            *(
                (requirements, ())
                for requirements in (
                    f"scrapy>={SCRAPY_ANCIENT_VERSION}",  # Ancient but not frozen
                    f"scrapy~={SCRAPY_INSECURE_VERSION}",  # Insecure but not frozen
                    f"scrapy!={SCRAPY_ANCIENT_VERSION}",  # Ancient but not frozen
                    "scrapy>=2.0.0,<3.0.0",  # Range specification
                )
            ),
            # SCP16 unmaintained packages
            (
                "scrapy-crawlera",
                (
                    Issue(
                        "SCP16 unmaintained requirement: replace with scrapy-zyte-smartproxy",
                        path=path,
                    ),
                ),
            ),
            (
                "scrapy-splash==1.2.3",
                (
                    Issue(
                        "SCP16 unmaintained requirement: replace with one of: scrapy-playwright, scrapy-zyte-api",
                        path=path,
                    ),
                ),
            ),
            # Signs of SCP13, like editable installs (-e), should not prevent
            # the reporting of SCP14/SCP15/SCP16.
            (
                "\n".join(
                    [
                        "-e git+https://github.com/scrapy/parsel.git#egg=parsel",
                        f"scrapy=={SCRAPY_ANCIENT_VERSION}",
                        "scrapy-crawlera~=1.0.0",
                    ]
                ),
                (
                    Issue(
                        f"SCP14 unsupported requirement: scrapy-flake8 only supports scrapy>={SCRAPY_LOWEST_SUPPORTED}+",
                        line=2,
                        path=path,
                    ),
                    Issue(
                        f"SCP15 insecure requirement: scrapy {SCRAPY_LOWEST_SAFE} implements security fixes",
                        line=2,
                        path=path,
                    ),
                    Issue(
                        "SCP16 unmaintained requirement: replace with scrapy-zyte-smartproxy",
                        line=3,
                        path=path,
                    ),
                ),
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


def test_version_constants():
    assert SCRAPY_HIGHEST_KNOWN is not None
    assert SCRAPY_LOWEST_SAFE is not None
    assert SCRAPY_LOWEST_SUPPORTED is not None

    assert SCRAPY_FUTURE_VERSION >= SCRAPY_HIGHEST_KNOWN
    assert SCRAPY_HIGHEST_KNOWN >= SCRAPY_LOWEST_SAFE
    assert SCRAPY_LOWEST_SAFE >= SCRAPY_INSECURE_VERSION
    assert SCRAPY_INSECURE_VERSION >= SCRAPY_LOWEST_SUPPORTED
    assert SCRAPY_LOWEST_SUPPORTED >= SCRAPY_ANCIENT_VERSION
