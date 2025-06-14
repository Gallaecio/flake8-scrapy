# scrapy-flake8

![](https://github.com/stummjr/flake8-scrapy/workflows/CI/badge.svg)
![](https://pepy.tech/badge/flake8-scrapy)

A [Flake8](https://flake8.pycqa.org/en/latest/) plugin to catch common issues
on Scrapy projects.


## Installation

```
pip install flake8-scrapy
```

## Initial setup

For all checks to work, you must:

-   Have a
    [`scrapy.cfg`](https://docs.scrapy.org/en/latest/topics/commands.html#default-structure-of-scrapy-projects)
    file in the root of your Scrapy project folder.

-   Have a `requirements.txt` file there as well.

-   Configure Flake8 to handle `requirements.txt` files. For example:

    ```
    # .flake8, setup.cfg or pyproject.toml
    [flake8]
    filename = *.py,requirements.txt
    ```


## Usage

Once installed and setup, flake8-scrapy checks are run automatically when
running Flake8:

```
flake8
```

When using [pre-commit](https://pre-commit.com/), configure Flake8 and list
flake8-scrapy in `additional_dependencies`. For example:

```yaml
- repo: https://github.com/pycqa/flake8
  rev: "7.2.0"
  hooks:
  - id: flake8
    additional_dependencies:
    - flake8-scrapy
```

## Error codes

| Code  | Meaning |
| ---   | --- |
| SCP01 | There are URLs in `start_urls` whose netloc is not in `allowed_domains` |
| SCP02 | There are URLs in `allowed_domains` |
| SCP03 | Use of `urljoin(response.url, '/foo')` instead of `response.urljoin('/foo')` |
| SCP04 | Use of `Selector(response)` in callback |
| SCP07 | Unknown setting |
| SCP08 | Deprecated setting |
| SCP09 | Setting requires upgrade |
| SCP10 | Removed setting |
| SCP11 | Duplicate requirement |
| SCP12 | Non-frozen requirement |
| SCP13 | Ancient Scrapy version |
| SCP14 | Insecure Scrapy version |
| SCP15 | Missing setting requirement |
| SCP16 | Obsolete requirement |
| SCP17 | Wrong setting getter |
| SCP18 | Invalid setting value |
| SCP19 | No project USER_AGENT |
| SCP20 | Project ROBOTSTXT_OBEY not enabled |
| SCP21 | Project throttling not set |
| SCP22 | No contact info |
| SCP23 | Redefined setting |
| SCP24 | Use of BASE setting |
| SCP25 | Unneeded setting get |
| SCP26 | Ignored getter default |
| SCP27 | Unneeded import path string |
| SCP28 | Unneeded filesystem path strings |
| SCP29 | Redefined setting default |
| SCP30 | Unpickleable setting value |
| SCP31 | Missing recomended setting |
| SCP32 | Missing setting with upcoming default value change |
| SCP33 | No-op setting definition |
| SCP34 | Unspecified --requirements-file |
| SCP35 | No default stack |
| SCP36 | Non-frozen stack |
| SCP37 | Different stacks |
| SCP38 | Missing stack requirememt |
| SCP39 | Different requirements |
| SCP40 | Conflicting requirement paths |

## Options

You can use the following additional options in your
[flake8 configuration](https://flake8.pycqa.org/en/latest/user/configuration.html)
to customize the behavior of flake8-scrapy:

### `known_scrapy_settings`

Default: `[]`

A list of Scrapy settings that will not raise SCP07, SCP08, SCP09, SCP10 or
SCP15 errors.

If you are using the latest version of flake8-scrapy and you find yourself
adding a setting to this list that is not specific to your project (i.e. made
up by yourself for some custom Scrapy component), consider
[opening an issue](https://github.com/stummjr/flake8-scrapy/issues) to request
support for that setting.

## Other recommended tools

In addition to flake8-scrapy, you may want to use the following tools:

- [ruff](https://docs.astral.sh/ruff/) for fast linting and formatting.

  For example,
  [multi-value-repeated-key-literal (F601)](https://docs.astral.sh/ruff/rules/multi-value-repeated-key-literal/)
  can detect accidental setting redefinitions in
  [`custom_settings`](https://docs.scrapy.org/en/latest/topics/spiders.html#scrapy.Spider.custom_settings).

- [mypy](https://mypy.readthedocs.io/en/stable/) for static type checking.

  For example, if you set
  [`start_urls`](https://docs.scrapy.org/en/latest/topics/spiders.html#scrapy.Spider.start_urls)
  to `"https://toscrape.com"`, mypy will report that `start_urls` must be a
  list of strings.

- [flake8-requirements](https://pypi.org/project/flake8-requirements/) to check for missing dependencies.
