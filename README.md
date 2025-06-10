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

-   Have a `scrapy.cfg` file in the root of your Scrapy project folder.

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
| SCP07 | Use of unknown settings |
| SCP08 | Use of settings deprecated in the target Scrapy and Scrapy plugin versions |
| SCP09 | Use of settings not yet available in the target Scrapy and Scrapy plugin versions |
| SCP10 | Use of old settings that have been removed from the target Scrapy and Scrapy plugin versions |
| SCP11 | Duplicate dependency in requirements.txt |
| SCP12 | Non-frozen dependency in requirements.txt |
| SCP13 | Ancient Scrapy version in requirements.txt |
| SCP14 | Insecure Scrapy version in requirements.txt |
| SCP15 | Use of setting of package not in requirements.txt |
| SCP16 | Obsolete package in requirements.txt |
| SCP17 | Wrong setting getter |
| SCP18 | Invalid setting value |
| SCP19 | USER_AGENT missing from settings.py |
| SCP20 | ROBOTSTXT_OBEY not enabled in settings.py |
| SCP21 | Throttling settings missing in settings.py |
| SCP22 | Missing contact info in USER_AGENT |
| SCP23 | Redefined setting in settings.py |
| SCP24 | Use of a BASE setting |
| SCP25 | Unneeded settings.get() |
| SCP26 | Ignored getter default |
| SCP27 | Unneeded import path strings |


## Options

You can use the following additional options in your
[flake8 configuration](https://flake8.pycqa.org/en/latest/user/configuration.html)
to customize the behavior of flake8-scrapy:

### `allow_scrapy_settings`

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
