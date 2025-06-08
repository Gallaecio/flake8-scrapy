# scrapy-flake8

![](https://github.com/stummjr/flake8-scrapy/workflows/CI/badge.svg)
![](https://pepy.tech/badge/flake8-scrapy)

A [Flake8](https://flake8.pycqa.org/en/latest/) plugin to catch common issues
on Scrapy projects.

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


## Options

You can use the following additional options in your
[flake8 configuration](https://flake8.pycqa.org/en/latest/user/configuration.html)
to customize the behavior of flake8-scrapy:

### `allow_scrapy_settings`

Default: `[]`

A list of Scrapy settings that will not raise SCP07, SCP08, SCP09 or SCP10
errors.

If you are using the latest version of flake8-scrapy and you find yourself
adding a setting to this list that is not specific to your project (i.e. made
up by yourself for some custom Scrapy component), consider
[opening an issue](https://github.com/stummjr/flake8-scrapy/issues) to request
support for that setting.


## Installation

```
pip install flake8-scrapy
```


## Usage

Once installed, flake8-scrapy checks are run automatically when running
[Flake8](https://flake8.pycqa.org/en/latest/):

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
