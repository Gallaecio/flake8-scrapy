from . import File, Issue, cases, load_sample_file
from .helpers import check_project


@cases(
    (
        *(
            (
                File(load_sample_file(sample), path),
                issues,
            )
            for path in ("a.py",)
            for sample, issues in (
                (
                    "allowed_domains.py",
                    tuple(
                        Issue(
                            "SCP01 allowed_domains doesn't allow this URL from start_urls",
                            path=path,
                            line=line,
                            column=8,
                        )
                        for line in (15, 16)
                    ),
                ),
                (
                    "url_in_allowed_domains.py",
                    Issue(
                        "SCP02 allowed_domains should not contain URLs",
                        11,
                        8,
                        path=path,
                    ),
                ),
            )
        ),
    )
)
def test_domains(input, expected):
    check_project(input, expected)
