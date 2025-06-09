from __future__ import annotations

import ast
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from difflib import get_close_matches
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from packaging.utils import canonicalize_name
from packaging.version import Version

from . import MINIMUM_SUPPORTED_SCRAPY_VERSION, IssueFinder

if TYPE_CHECKING:
    from collections.abc import Generator

MIN_VALID_SETTING_NAME_LENGTH = 3


class SettingType(Enum):
    BOOL = "bool"
    INT = "int"
    FLOAT = "float"
    LIST = "list"
    DICT = "dict"
    DICT_OR_LIST = "dict_or_list"
    BASED_DICT = "based_dict"
    OPT_STR = "opt_str"
    STR = "str"
    CLS = "cls"
    PATH = "path"
    OPT_PATH = "opt_path"
    LOG_LEVEL = "log_level"
    ENUM_STR = "enum_str"
    PERIODIC_LOG_CONFIG = "periodic_log_config"
    OPT_CALLABLE = "opt_callable"
    OPT_INT = "opt_int"


class AllowedExcludeSettingsMixin:
    def _init_allowed_exclude_settings(
        self, allowed_settings=None, exclude_settings=None
    ):
        self.allowed_settings = set(allowed_settings) if allowed_settings else set()
        self.exclude_settings = set(exclude_settings) if exclude_settings else set()


@dataclass
class SettingInfo:
    added_version: str | None = None
    removed_version: str | None = None
    deprecated_version: str | None = None
    deprecation_message: str | None = None
    package: str = "scrapy"
    type: SettingType | None = None
    has_default: bool | None = None
    allowed_values: tuple[str, ...] | None = None

    def __post_init__(self):
        if self.has_default is None:
            self.has_default = self.package == "scrapy"


# Grouped by active, deprecated, removed, and plugin-specific.
# Active settings are sorted as in scrapy.settings.default_settings, while
# deprecated and removed settings are sorted by the version that deprecated or
# removed them, from higher to lower.
SETTINGS = {
    # Active settings
    "ADDONS": SettingInfo(added_version="2.10.0", type=SettingType.DICT),
    "AWS_ACCESS_KEY_ID": SettingInfo(type=SettingType.OPT_STR),
    "AWS_SECRET_ACCESS_KEY": SettingInfo(type=SettingType.OPT_STR),
    "AWS_SESSION_TOKEN": SettingInfo(type=SettingType.OPT_STR),
    "AWS_ENDPOINT_URL": SettingInfo(type=SettingType.OPT_STR),
    "AWS_USE_SSL": SettingInfo(type=SettingType.BOOL),
    "AWS_VERIFY": SettingInfo(type=SettingType.BOOL),
    "AWS_REGION_NAME": SettingInfo(type=SettingType.OPT_STR),
    "ASYNCIO_EVENT_LOOP": SettingInfo(added_version="2.4.0", type=SettingType.CLS),
    "AUTOTHROTTLE_DEBUG": SettingInfo(type=SettingType.BOOL),
    "AUTOTHROTTLE_ENABLED": SettingInfo(type=SettingType.BOOL),
    "AUTOTHROTTLE_MAX_DELAY": SettingInfo(type=SettingType.FLOAT),
    "AUTOTHROTTLE_START_DELAY": SettingInfo(type=SettingType.FLOAT),
    "AUTOTHROTTLE_TARGET_CONCURRENCY": SettingInfo(type=SettingType.FLOAT),
    "BOT_NAME": SettingInfo(type=SettingType.STR),
    "CLOSESPIDER_ERRORCOUNT": SettingInfo(type=SettingType.INT),
    "CLOSESPIDER_ITEMCOUNT": SettingInfo(type=SettingType.INT),
    "CLOSESPIDER_PAGECOUNT": SettingInfo(type=SettingType.INT),
    "CLOSESPIDER_PAGECOUNT_NO_ITEM": SettingInfo(
        type=SettingType.INT, added_version="2.12.0"
    ),
    "CLOSESPIDER_TIMEOUT": SettingInfo(type=SettingType.FLOAT),
    "CLOSESPIDER_TIMEOUT_NO_ITEM": SettingInfo(
        type=SettingType.INT, added_version="2.10.0"
    ),
    "COMMANDS_MODULE": SettingInfo(type=SettingType.STR),
    "COMPRESSION_ENABLED": SettingInfo(type=SettingType.BOOL),
    "CONCURRENT_ITEMS": SettingInfo(type=SettingType.INT),
    "CONCURRENT_REQUESTS": SettingInfo(type=SettingType.INT),
    "CONCURRENT_REQUESTS_PER_DOMAIN": SettingInfo(type=SettingType.INT),
    "CONCURRENT_REQUESTS_PER_IP": SettingInfo(type=SettingType.INT),
    "COOKIES_DEBUG": SettingInfo(type=SettingType.BOOL),
    "COOKIES_ENABLED": SettingInfo(type=SettingType.BOOL),
    "DEFAULT_DROPITEM_LOG_LEVEL": SettingInfo(
        added_version="2.13.0", type=SettingType.LOG_LEVEL
    ),
    "DEFAULT_ITEM_CLASS": SettingInfo(type=SettingType.CLS),
    "DEFAULT_REQUEST_HEADERS": SettingInfo(type=SettingType.DICT),
    "DEPTH_LIMIT": SettingInfo(type=SettingType.INT),
    "DEPTH_PRIORITY": SettingInfo(type=SettingType.INT),
    "DEPTH_STATS_VERBOSE": SettingInfo(type=SettingType.BOOL),
    "DNSCACHE_ENABLED": SettingInfo(type=SettingType.BOOL),
    "DNSCACHE_SIZE": SettingInfo(type=SettingType.INT),
    "DNS_RESOLVER": SettingInfo(type=SettingType.CLS),
    "DNS_TIMEOUT": SettingInfo(type=SettingType.FLOAT),
    "DOWNLOAD_DELAY": SettingInfo(type=SettingType.FLOAT),
    "DOWNLOAD_FAIL_ON_DATALOSS": SettingInfo(type=SettingType.BOOL),
    "DOWNLOAD_HANDLERS": SettingInfo(type=SettingType.BASED_DICT),
    "DOWNLOAD_HANDLERS_BASE": SettingInfo(),
    "DOWNLOAD_MAXSIZE": SettingInfo(type=SettingType.INT),
    "DOWNLOAD_SLOTS": SettingInfo(type=SettingType.DICT, added_version="2.9.0"),
    "DOWNLOAD_TIMEOUT": SettingInfo(type=SettingType.FLOAT),
    "DOWNLOAD_WARNSIZE": SettingInfo(type=SettingType.INT),
    "DOWNLOADER": SettingInfo(type=SettingType.CLS),
    "DOWNLOADER_CLIENT_TLS_CIPHERS": SettingInfo(type=SettingType.STR),
    "DOWNLOADER_CLIENT_TLS_METHOD": SettingInfo(
        type=SettingType.ENUM_STR,
        allowed_values=("TLS", "TLSv1.0", "TLSv1.1", "TLSv1.2"),
    ),
    "DOWNLOADER_CLIENT_TLS_VERBOSE_LOGGING": SettingInfo(type=SettingType.BOOL),
    "DOWNLOADER_CLIENTCONTEXTFACTORY": SettingInfo(type=SettingType.CLS),
    "DOWNLOADER_HTTPCLIENTFACTORY": SettingInfo(type=SettingType.CLS),
    "DOWNLOADER_MIDDLEWARES": SettingInfo(type=SettingType.BASED_DICT),
    "DOWNLOADER_MIDDLEWARES_BASE": SettingInfo(),
    "DOWNLOADER_STATS": SettingInfo(type=SettingType.BOOL),
    "DUPEFILTER_CLASS": SettingInfo(type=SettingType.CLS),
    "DUPEFILTER_DEBUG": SettingInfo(type=SettingType.BOOL),
    "EDITOR": SettingInfo(type=SettingType.STR),
    "EXTENSIONS": SettingInfo(type=SettingType.BASED_DICT),
    "EXTENSIONS_BASE": SettingInfo(),
    "FEED_EXPORT_BATCH_ITEM_COUNT": SettingInfo(
        added_version="2.3.0", type=SettingType.INT
    ),
    "FEED_EXPORT_ENCODING": SettingInfo(type=SettingType.OPT_STR),
    "FEED_EXPORT_FIELDS": SettingInfo(type=SettingType.DICT_OR_LIST),
    "FEED_EXPORT_INDENT": SettingInfo(type=SettingType.OPT_INT),
    "FEED_EXPORTERS": SettingInfo(type=SettingType.BASED_DICT),
    "FEED_EXPORTERS_BASE": SettingInfo(),
    "FEED_STORAGE_FTP_ACTIVE": SettingInfo(type=SettingType.BOOL),
    "FEED_STORAGE_GCS_ACL": SettingInfo(
        added_version="2.3.0", type=SettingType.OPT_STR
    ),
    "FEED_STORAGE_S3_ACL": SettingInfo(type=SettingType.OPT_STR),
    "FEED_STORE_EMPTY": SettingInfo(type=SettingType.BOOL),
    "FEED_STORAGES": SettingInfo(type=SettingType.BASED_DICT),
    "FEED_STORAGES_BASE": SettingInfo(),
    "FEED_TEMPDIR": SettingInfo(type=SettingType.OPT_PATH),
    "FEED_URI_PARAMS": SettingInfo(type=SettingType.OPT_CALLABLE),
    "FEEDS": SettingInfo(added_version="2.1.0", type=SettingType.DICT),
    "FILES_EXPIRES": SettingInfo(type=SettingType.INT),
    "FILES_RESULT_FIELD": SettingInfo(type=SettingType.OPT_STR),
    "FILES_STORE": SettingInfo(type=SettingType.OPT_PATH),
    "FILES_STORE_GCS_ACL": SettingInfo(type=SettingType.OPT_STR),
    "FILES_STORE_S3_ACL": SettingInfo(type=SettingType.OPT_STR),
    "FILES_URLS_FIELD": SettingInfo(type=SettingType.OPT_STR),
    "FORCE_CRAWLER_PROCESS": SettingInfo(),
    "FTP_PASSIVE_MODE": SettingInfo(type=SettingType.BOOL),
    "FTP_PASSWORD": SettingInfo(type=SettingType.OPT_STR),
    "FTP_USER": SettingInfo(type=SettingType.OPT_STR),
    "GCS_PROJECT_ID": SettingInfo(added_version="2.3.0", type=SettingType.OPT_STR),
    "HTTPCACHE_ALWAYS_STORE": SettingInfo(type=SettingType.BOOL),
    "HTTPCACHE_DBM_MODULE": SettingInfo(type=SettingType.OPT_STR),
    "HTTPCACHE_DIR": SettingInfo(type=SettingType.OPT_PATH),
    "HTTPCACHE_ENABLED": SettingInfo(type=SettingType.BOOL),
    "HTTPCACHE_EXPIRATION_SECS": SettingInfo(type=SettingType.INT),
    "HTTPCACHE_GZIP": SettingInfo(type=SettingType.BOOL),
    "HTTPCACHE_IGNORE_HTTP_CODES": SettingInfo(type=SettingType.LIST),
    "HTTPCACHE_IGNORE_MISSING": SettingInfo(type=SettingType.BOOL),
    "HTTPCACHE_IGNORE_RESPONSE_CACHE_CONTROLS": SettingInfo(type=SettingType.LIST),
    "HTTPCACHE_IGNORE_SCHEMES": SettingInfo(type=SettingType.LIST),
    "HTTPCACHE_POLICY": SettingInfo(type=SettingType.CLS),
    "HTTPCACHE_STORAGE": SettingInfo(type=SettingType.CLS),
    "HTTPERROR_ALLOW_ALL": SettingInfo(type=SettingType.BOOL),
    "HTTPERROR_ALLOWED_CODES": SettingInfo(type=SettingType.LIST),
    "HTTPPROXY_AUTH_ENCODING": SettingInfo(type=SettingType.OPT_STR),
    "HTTPPROXY_ENABLED": SettingInfo(type=SettingType.BOOL),
    "IMAGES_EXPIRES": SettingInfo(type=SettingType.INT),
    "IMAGES_MIN_HEIGHT": SettingInfo(type=SettingType.INT),
    "IMAGES_MIN_WIDTH": SettingInfo(type=SettingType.INT),
    "IMAGES_RESULT_FIELD": SettingInfo(type=SettingType.OPT_STR),
    "IMAGES_STORE": SettingInfo(type=SettingType.OPT_PATH),
    "IMAGES_STORE_GCS_ACL": SettingInfo(type=SettingType.OPT_STR),
    "IMAGES_STORE_S3_ACL": SettingInfo(type=SettingType.OPT_STR),
    "IMAGES_THUMBS": SettingInfo(type=SettingType.DICT),
    "IMAGES_URLS_FIELD": SettingInfo(type=SettingType.OPT_STR),
    "ITEM_PIPELINES": SettingInfo(type=SettingType.BASED_DICT),
    "ITEM_PIPELINES_BASE": SettingInfo(),
    "ITEM_PROCESSOR": SettingInfo(type=SettingType.CLS),
    "JOBDIR": SettingInfo(type=SettingType.OPT_PATH),
    "LOG_DATEFORMAT": SettingInfo(type=SettingType.STR),
    "LOG_ENABLED": SettingInfo(type=SettingType.BOOL),
    "LOG_ENCODING": SettingInfo(type=SettingType.STR),
    "LOG_FILE": SettingInfo(type=SettingType.OPT_PATH),
    "LOG_FILE_APPEND": SettingInfo(added_version="2.6.0", type=SettingType.BOOL),
    "LOG_FORMAT": SettingInfo(type=SettingType.STR),
    "LOG_FORMATTER": SettingInfo(type=SettingType.CLS),
    "LOG_LEVEL": SettingInfo(type=SettingType.LOG_LEVEL),
    "LOG_SHORT_NAMES": SettingInfo(type=SettingType.BOOL),
    "LOG_STDOUT": SettingInfo(type=SettingType.BOOL),
    "LOG_VERSIONS": SettingInfo(added_version="2.13.0", type=SettingType.LIST),
    "LOGSTATS_INTERVAL": SettingInfo(type=SettingType.FLOAT),
    "MAIL_FROM": SettingInfo(type=SettingType.OPT_STR),
    "MAIL_HOST": SettingInfo(type=SettingType.OPT_STR),
    "MAIL_PASS": SettingInfo(type=SettingType.OPT_STR),
    "MAIL_PORT": SettingInfo(type=SettingType.OPT_STR),
    "MAIL_USER": SettingInfo(type=SettingType.OPT_STR),
    "MAIL_TLS": SettingInfo(type=SettingType.BOOL),
    "MAIL_SSL": SettingInfo(type=SettingType.BOOL),
    "MEDIA_ALLOW_REDIRECTS": SettingInfo(type=SettingType.BOOL),
    "MEMDEBUG_ENABLED": SettingInfo(type=SettingType.BOOL),
    "MEMDEBUG_NOTIFY": SettingInfo(type=SettingType.LIST),
    "MEMUSAGE_CHECK_INTERVAL_SECONDS": SettingInfo(type=SettingType.FLOAT),
    "MEMUSAGE_ENABLED": SettingInfo(type=SettingType.BOOL),
    "MEMUSAGE_LIMIT_MB": SettingInfo(type=SettingType.INT),
    "MEMUSAGE_NOTIFY_MAIL": SettingInfo(type=SettingType.LIST),
    "MEMUSAGE_WARNING_MB": SettingInfo(type=SettingType.INT),
    "METAREFRESH_ENABLED": SettingInfo(type=SettingType.BOOL),
    "METAREFRESH_IGNORE_TAGS": SettingInfo(type=SettingType.LIST),
    "METAREFRESH_MAXDELAY": SettingInfo(type=SettingType.INT),
    "NEWSPIDER_MODULE": SettingInfo(type=SettingType.STR),
    "PERIODIC_LOG_DELTA": SettingInfo(
        added_version="2.11.0", type=SettingType.PERIODIC_LOG_CONFIG
    ),
    "PERIODIC_LOG_STATS": SettingInfo(
        added_version="2.11.0", type=SettingType.PERIODIC_LOG_CONFIG
    ),
    "PERIODIC_LOG_TIMING_ENABLED": SettingInfo(
        added_version="2.11.0", type=SettingType.BOOL
    ),
    "RANDOMIZE_DOWNLOAD_DELAY": SettingInfo(type=SettingType.BOOL),
    "REACTOR_THREADPOOL_MAXSIZE": SettingInfo(type=SettingType.INT),
    "REDIRECT_ENABLED": SettingInfo(type=SettingType.BOOL),
    "REDIRECT_MAX_TIMES": SettingInfo(type=SettingType.INT),
    "REDIRECT_PRIORITY_ADJUST": SettingInfo(type=SettingType.INT),
    "REFERER_ENABLED": SettingInfo(type=SettingType.BOOL),
    "REFERRER_POLICY": SettingInfo(type=SettingType.CLS),
    "REQUEST_FINGERPRINTER_CLASS": SettingInfo(
        added_version="2.7.0", type=SettingType.CLS
    ),
    "RETRY_ENABLED": SettingInfo(type=SettingType.BOOL),
    "RETRY_EXCEPTIONS": SettingInfo(added_version="2.10.0", type=SettingType.LIST),
    "RETRY_HTTP_CODES": SettingInfo(type=SettingType.LIST),
    "RETRY_PRIORITY_ADJUST": SettingInfo(type=SettingType.INT),
    "RETRY_TIMES": SettingInfo(type=SettingType.INT),
    "ROBOTSTXT_OBEY": SettingInfo(type=SettingType.BOOL),
    "ROBOTSTXT_PARSER": SettingInfo(type=SettingType.CLS),
    "ROBOTSTXT_USER_AGENT": SettingInfo(type=SettingType.OPT_STR),
    "SCHEDULER": SettingInfo(type=SettingType.CLS),
    "SCHEDULER_DEBUG": SettingInfo(type=SettingType.BOOL),
    "SCHEDULER_DISK_QUEUE": SettingInfo(type=SettingType.CLS),
    "SCHEDULER_MEMORY_QUEUE": SettingInfo(type=SettingType.CLS),
    "SCHEDULER_PRIORITY_QUEUE": SettingInfo(type=SettingType.CLS),
    "SCHEDULER_START_DISK_QUEUE": SettingInfo(
        added_version="2.13.0", type=SettingType.CLS
    ),
    "SCHEDULER_START_MEMORY_QUEUE": SettingInfo(
        added_version="2.13.0", type=SettingType.CLS
    ),
    "SCRAPER_SLOT_MAX_ACTIVE_SIZE": SettingInfo(type=SettingType.INT),
    "SPIDER_CONTRACTS": SettingInfo(type=SettingType.BASED_DICT),
    "SPIDER_CONTRACTS_BASE": SettingInfo(),
    "SPIDER_LOADER_CLASS": SettingInfo(type=SettingType.CLS),
    "SPIDER_LOADER_WARN_ONLY": SettingInfo(type=SettingType.BOOL),
    "SPIDER_MIDDLEWARES": SettingInfo(type=SettingType.BASED_DICT),
    "SPIDER_MIDDLEWARES_BASE": SettingInfo(),
    "SPIDER_MODULES": SettingInfo(type=SettingType.LIST),
    "STATS_CLASS": SettingInfo(type=SettingType.CLS),
    "STATS_DUMP": SettingInfo(type=SettingType.BOOL),
    "STATSMAILER_RCPTS": SettingInfo(type=SettingType.LIST),
    "TELNETCONSOLE_ENABLED": SettingInfo(type=SettingType.BOOL),
    "TELNETCONSOLE_HOST": SettingInfo(type=SettingType.STR),
    "TELNETCONSOLE_PASSWORD": SettingInfo(type=SettingType.OPT_STR),
    "TELNETCONSOLE_PORT": SettingInfo(type=SettingType.LIST),
    "TELNETCONSOLE_USERNAME": SettingInfo(type=SettingType.STR),
    "TEMPLATES_DIR": SettingInfo(type=SettingType.OPT_PATH),
    "TWISTED_REACTOR": SettingInfo(type=SettingType.CLS),
    "URLLENGTH_LIMIT": SettingInfo(type=SettingType.INT),
    "USER_AGENT": SettingInfo(type=SettingType.OPT_STR),
    "WARN_ON_GENERATOR_RETURN_VALUE": SettingInfo(
        added_version="2.13.0", type=SettingType.BOOL
    ),
    # Deprecated settings
    "AJAXCRAWL_ENABLED": SettingInfo(
        added_version="0.22.0",
        deprecated_version="2.13.0",
        deprecation_message=(
            "The setting is False by default, and setting it to True will stop"
            " working in a future version of Scrapy."
        ),
        type=SettingType.BOOL,
    ),
    "REQUEST_FINGERPRINTER_IMPLEMENTATION": SettingInfo(
        added_version="2.7.0",
        deprecated_version="2.12.0",
        deprecation_message=(
            "See https://flake8-scrapy.readthedocs.io/en/latest/rules/scp08.html"
            "#request_fingerprinter_implementation"
        ),
    ),
    "FEED_FORMAT": SettingInfo(
        deprecated_version="2.1.0",
        deprecation_message="Use FEEDS instead",
    ),
    "FEED_URI": SettingInfo(
        deprecated_version="2.1.0",
        deprecation_message="Use FEEDS instead",
    ),
    # Removed settings
    "SPIDER_MANAGER_CLASS": SettingInfo(
        removed_version="2.5.0", deprecated_version="1.0.0"
    ),
    "LOG_UNSERIALIZABLE_REQUESTS": SettingInfo(
        removed_version="2.1.0",
        deprecated_version=MINIMUM_SUPPORTED_SCRAPY_VERSION,
        deprecation_message="Use SCHEDULER_DEBUG instead.",
    ),
    "REDIRECT_MAX_METAREFRESH_DELAY": SettingInfo(
        removed_version="2.1.0",
        deprecated_version=MINIMUM_SUPPORTED_SCRAPY_VERSION,
        deprecation_message="Use METAREFRESH_MAXDELAY instead.",
    ),
    # scrapy-feedexporter-azure-storage plugin settings, in order of appearance
    # in https://github.com/scrapy-plugins/scrapy-feedexporter-azure-storage
    "AZURE_CONNECTION_STRING": SettingInfo(package="scrapy-feedexporter-azure-storage"),
    "AZURE_ACCOUNT_URL_WITH_SAS_TOKEN": SettingInfo(
        package="scrapy-feedexporter-azure-storage"
    ),
    "AZURE_ACCOUNT_URL": SettingInfo(package="scrapy-feedexporter-azure-storage"),
    "AZURE_ACCOUNT_KEY": SettingInfo(package="scrapy-feedexporter-azure-storage"),
    # scrapy-deltafetch plugin settings, in order of appearance in
    # https://github.com/scrapy-plugins/scrapy-deltafetch#usage
    "DELTAFETCH_ENABLED": SettingInfo(
        package="scrapy-deltafetch", type=SettingType.BOOL
    ),
    "DELTAFETCH_DIR": SettingInfo(package="scrapy-deltafetch"),
    "DELTAFETCH_RESET": SettingInfo(package="scrapy-deltafetch"),
    # scrapy-feedexporter-dropbox plugin settings, in order of appearance in
    # https://github.com/scrapy-plugins/scrapy-feedexporter-dropbox
    "DROPBOX_API_TOKEN": SettingInfo(package="scrapy-feedexporter-dropbox"),
    # scrapy-frontera plugin settings, in order of appearance in
    # https://github.com/scrapinghub/scrapy-frontera#usage-and-features
    "FRONTERA_SCHEDULER_START_REQUESTS_TO_FRONTIER": SettingInfo(
        package="scrapy-frontera"
    ),
    "FRONTERA_SCHEDULER_REQUEST_CALLBACKS_TO_FRONTIER": SettingInfo(
        package="scrapy-frontera"
    ),
    "FRONTERA_SCHEDULER_STATE_ATTRIBUTES": SettingInfo(package="scrapy-frontera"),
    "FRONTERA_SCHEDULER_CALLBACK_SLOT_PREFIX_MAP": SettingInfo(
        package="scrapy-frontera"
    ),
    "BACKEND": SettingInfo(package="scrapy-frontera"),
    # scrapy-feedexporter-google-drive plugin settings, in order of appearance
    # in https://github.com/scrapy-plugins/scrapy-feedexporter-google-drive
    "GDRIVE_SERVICE_ACCOUNT_CREDENTIALS_JSON": SettingInfo(
        package="scrapy-feedexporter-google-drive"
    ),
    # scrapy-feedexporter-google-sheets plugin settings, in order of appearance
    # in https://github.com/scrapy-plugins/scrapy-feedexporter-google-sheets
    "GOOGLE_CREDENTIALS": SettingInfo(package="scrapy-feedexporter-google-sheets"),
    # hcf-backend plugin settings, in order of appearance in
    # https://github.com/scrapinghub/hcf-backend/blob/master/hcf_backend/backend.py
    "HCF_CONSUMER_MAX_REQUESTS": SettingInfo(package="hcf-backend"),
    "HCF_CONSUMER_MAX_BATCHES": SettingInfo(package="hcf-backend"),
    "MAX_NEXT_REQUESTS": SettingInfo(package="hcf-backend"),
    "HCF_AUTH": SettingInfo(package="hcf-backend"),
    "HCF_PROJECT_ID": SettingInfo(package="hcf-backend"),
    "HCF_PRODUCER_FRONTIER": SettingInfo(package="hcf-backend"),
    "HCF_PRODUCER_SLOT_PREFIX": SettingInfo(package="hcf-backend"),
    "HCF_PRODUCER_NUMBER_OF_SLOTS": SettingInfo(package="hcf-backend"),
    "HCF_PRODUCER_BATCH_SIZE": SettingInfo(package="hcf-backend"),
    "HCF_CONSUMER_FRONTIER": SettingInfo(package="hcf-backend"),
    "HCF_CONSUMER_SLOT": SettingInfo(package="hcf-backend"),
    "HCF_CONSUMER_DONT_DELETE_REQUESTS": SettingInfo(package="hcf-backend"),
    "HCF_CONSUMER_DELETE_BATCHES_ON_STOP": SettingInfo(package="hcf-backend"),
    # scrapy-incremental plugin settings, in order of appearance in
    # https://github.com/scrapy-plugins/scrapy-incremental
    "SCRAPYCLOUD_API_KEY": SettingInfo(package="scrapy-incremental"),
    "SCRAPYCLOUD_PROJECT_ID": SettingInfo(package="scrapy-incremental"),
    "INCREMENTAL_PIPELINE_ITEM_UNIQUE_FIELD": SettingInfo(package="scrapy-incremental"),
    "INCREMENTAL_PIPELINE_BATCH_SIZE": SettingInfo(package="scrapy-incremental"),
    # scrapy-feedexporter-onedrive plugin settings, in order of appearance in
    # https://github.com/scrapy-plugins/scrapy-feedexporter-onedrive
    "ONEDRIVE_ACCESS_TOKEN": SettingInfo(package="scrapy-feedexporter-onedrive"),
    # scrapy-playwright plugin settings, in order of appearance in
    # https://github.com/scrapy-plugins/scrapy-playwright#supported-settings
    "PLAYWRIGHT_BROWSER_TYPE": SettingInfo(package="scrapy-playwright"),
    "PLAYWRIGHT_LAUNCH_OPTIONS": SettingInfo(package="scrapy-playwright"),
    "PLAYWRIGHT_CDP_URL": SettingInfo(package="scrapy-playwright"),
    "PLAYWRIGHT_CONNECT_URL": SettingInfo(package="scrapy-playwright"),
    "PLAYWRIGHT_CONNECT_KWARGS": SettingInfo(package="scrapy-playwright"),
    "PLAYWRIGHT_CONTEXTS": SettingInfo(package="scrapy-playwright"),
    "PLAYWRIGHT_MAX_CONTEXTS": SettingInfo(package="scrapy-playwright"),
    "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": SettingInfo(package="scrapy-playwright"),
    "PLAYWRIGHT_PROCESS_REQUEST_HEADERS": SettingInfo(package="scrapy-playwright"),
    "PLAYWRIGHT_RESTART_DISCONNECTED_BROWSER": SettingInfo(package="scrapy-playwright"),
    "PLAYWRIGHT_MAX_PAGES_PER_CONTEXT": SettingInfo(package="scrapy-playwright"),
    "PLAYWRIGHT_ABORT_REQUEST": SettingInfo(package="scrapy-playwright"),
    # scrapy-poet plugin settings, in order of appearance in
    # https://scrapy-poet.readthedocs.io/en/stable/settings.html
    "SCRAPY_POET_CACHE": SettingInfo(package="scrapy-poet"),
    "SCRAPY_POET_CACHE_ERRORS": SettingInfo(package="scrapy-poet"),
    "SCRAPY_POET_DISCOVER": SettingInfo(package="scrapy-poet"),
    "SCRAPY_POET_OVERRIDES": SettingInfo(
        deprecated_version="0.9.0",
        deprecation_message="Use SCRAPY_POET_DISCOVER and/or SCRAPY_POET_RULES instead",
        package="scrapy-poet",
    ),
    "SCRAPY_POET_PROVIDERS": SettingInfo(package="scrapy-poet"),
    "SCRAPY_POET_REQUEST_FINGERPRINTER_BASE_CLASS": SettingInfo(package="scrapy-poet"),
    "SCRAPY_POET_RULES": SettingInfo(package="scrapy-poet"),
    "SCRAPY_POET_TESTS_ADAPTER": SettingInfo(package="scrapy-poet"),
    "SCRAPY_POET_TESTS_DIR": SettingInfo(package="scrapy-poet"),
    # scrapy-redis plugin settings, in order of appearance in
    # https://github.com/rmax/scrapy-redis/wiki/Usage
    "SCHEDULER_SERIALIZER": SettingInfo(package="scrapy-redis"),
    "SCHEDULER_PERSIST": SettingInfo(package="scrapy-redis"),
    "SCHEDULER_QUEUE_CLASS": SettingInfo(package="scrapy-redis"),
    "SCHEDULER_IDLE_BEFORE_CLOSE": SettingInfo(package="scrapy-redis"),
    "REDIS_ITEMS_KEY": SettingInfo(package="scrapy-redis"),
    "REDIS_ITEMS_SERIALIZER": SettingInfo(package="scrapy-redis"),
    "REDIS_HOST": SettingInfo(package="scrapy-redis"),
    "REDIS_PORT": SettingInfo(package="scrapy-redis"),
    "REDIS_URL": SettingInfo(package="scrapy-redis"),
    "REDIS_PARAMS": SettingInfo(package="scrapy-redis"),
    "REDIS_START_URLS_AS_SET": SettingInfo(package="scrapy-redis"),
    "REDIS_START_URLS_KEY": SettingInfo(package="scrapy-redis"),
    "REDIS_ENCODING": SettingInfo(package="scrapy-redis"),
    # scrapyrt plugin settings, in order of appearance in
    # https://scrapyrt.readthedocs.io/en/latest/api.html#available-settings
    "SERVICE_ROOT": SettingInfo(package="scrapyrt"),
    "CRAWL_MANAGER": SettingInfo(package="scrapyrt"),
    "RESOURCES": SettingInfo(package="scrapyrt"),
    "LOG_DIR": SettingInfo(package="scrapyrt"),
    "TIMEOUT_LIMIT": SettingInfo(package="scrapyrt"),
    "DEBUG": SettingInfo(package="scrapyrt"),
    "PROJECT_SETTINGS": SettingInfo(package="scrapyrt"),
    # scrapy-settings-log plugin settings, in order of appearance in
    # https://github.com/scrapy-plugins/scrapy-settings-log
    "SETTINGS_LOGGING_ENABLED": SettingInfo(
        package="scrapy-settings-log", type=SettingType.BOOL
    ),
    "SETTINGS_LOGGING_REGEX": SettingInfo(package="scrapy-settings-log"),
    "SETTINGS_LOGGING_INDENT": SettingInfo(package="scrapy-settings-log"),
    "MASKED_SENSITIVE_SETTINGS_ENABLED": SettingInfo(
        package="scrapy-settings-log", type=SettingType.BOOL
    ),
    # scrapy-feedexporter-sftp plugin settings, in order of appearance in
    # https://github.com/scrapy-plugins/scrapy-feedexporter-sftp
    "FEED_STORAGE_SFTP_PKEY": SettingInfo(package="scrapy-feedexporter-sftp"),
    # spidermon plugin settings, in order of appearance in
    # https://spidermon.readthedocs.io/en/latest/settings.html
    "SPIDERMON_ENABLED": SettingInfo(package="spidermon", type=SettingType.BOOL),
    "SPIDERMON_EXPRESSIONS_MONITOR_CLASS": SettingInfo(package="spidermon"),
    "SPIDERMON_PERIODIC_MONITORS": SettingInfo(package="spidermon"),
    "SPIDERMON_SPIDER_CLOSE_MONITORS": SettingInfo(package="spidermon"),
    "SPIDERMON_SPIDER_CLOSE_EXPRESSION_MONITORS": SettingInfo(package="spidermon"),
    "SPIDERMON_SPIDER_OPEN_MONITORS": SettingInfo(package="spidermon"),
    "SPIDERMON_SPIDER_OPEN_EXPRESSION_MONITORS": SettingInfo(package="spidermon"),
    "SPIDERMON_ENGINE_STOP_MONITORS": SettingInfo(package="spidermon"),
    "SPIDERMON_ENGINE_STOP_EXPRESSION_MONITORS": SettingInfo(package="spidermon"),
    "SPIDERMON_ADD_FIELD_COVERAGE": SettingInfo(package="spidermon"),
    "SPIDERMON_FIELD_COVERAGE_SKIP_NONE": SettingInfo(package="spidermon"),
    "SPIDERMON_LIST_FIELDS_COVERAGE_LEVELS": SettingInfo(package="spidermon"),
    "SPIDERMON_DICT_FIELDS_COVERAGE_LEVELS": SettingInfo(package="spidermon"),
    "SPIDERMON_MONITOR_SKIPPING_RULES": SettingInfo(package="spidermon"),
    # scrapy-zyte-api plugin settings, in order of appearance in
    # https://scrapy-zyte-api.readthedocs.io/en/latest/reference/settings.html
    "ZYTE_API_AUTO_FIELD_STATS": SettingInfo(package="scrapy-zyte-api"),
    "ZYTE_API_AUTOMAP_PARAMS": SettingInfo(package="scrapy-zyte-api"),
    "ZYTE_API_BROWSER_HEADERS": SettingInfo(package="scrapy-zyte-api"),
    "ZYTE_API_COOKIE_MIDDLEWARE": SettingInfo(package="scrapy-zyte-api"),
    "ZYTE_API_DEFAULT_PARAMS": SettingInfo(package="scrapy-zyte-api"),
    "ZYTE_API_ENABLED": SettingInfo(package="scrapy-zyte-api", type=SettingType.BOOL),
    "ZYTE_API_EXPERIMENTAL_COOKIES_ENABLED": SettingInfo(
        package="scrapy-zyte-api", type=SettingType.BOOL
    ),
    "ZYTE_API_FALLBACK_HTTP_HANDLER": SettingInfo(package="scrapy-zyte-api"),
    "ZYTE_API_FALLBACK_HTTPS_HANDLER": SettingInfo(package="scrapy-zyte-api"),
    "ZYTE_API_FALLBACK_REQUEST_FINGERPRINTER_CLASS": SettingInfo(
        package="scrapy-zyte-api"
    ),
    "ZYTE_API_KEY": SettingInfo(package="scrapy-zyte-api"),
    "ZYTE_API_LOG_REQUESTS": SettingInfo(package="scrapy-zyte-api"),
    "ZYTE_API_LOG_REQUESTS_TRUNCATE": SettingInfo(package="scrapy-zyte-api"),
    "ZYTE_API_MAX_COOKIES": SettingInfo(package="scrapy-zyte-api"),
    "ZYTE_API_MAX_REQUESTS": SettingInfo(package="scrapy-zyte-api"),
    "ZYTE_API_PRESERVE_DELAY": SettingInfo(package="scrapy-zyte-api"),
    "ZYTE_API_PROVIDER_PARAMS": SettingInfo(package="scrapy-zyte-api"),
    "ZYTE_API_REFERRER_POLICY": SettingInfo(package="scrapy-zyte-api"),
    "ZYTE_API_RETRY_POLICY": SettingInfo(package="scrapy-zyte-api"),
    "ZYTE_API_SESSION_CHECKER": SettingInfo(package="scrapy-zyte-api"),
    "ZYTE_API_SESSION_ENABLED": SettingInfo(
        package="scrapy-zyte-api", type=SettingType.BOOL
    ),
    "ZYTE_API_SESSION_LOCATION": SettingInfo(package="scrapy-zyte-api"),
    "ZYTE_API_SESSION_MAX_BAD_INITS": SettingInfo(package="scrapy-zyte-api"),
    "ZYTE_API_SESSION_MAX_BAD_INITS_PER_POOL": SettingInfo(package="scrapy-zyte-api"),
    "ZYTE_API_SESSION_MAX_CHECK_FAILURES": SettingInfo(package="scrapy-zyte-api"),
    "ZYTE_API_SESSION_MAX_ERRORS": SettingInfo(package="scrapy-zyte-api"),
    "ZYTE_API_SESSION_PARAMS": SettingInfo(package="scrapy-zyte-api"),
    "ZYTE_API_SESSION_POOL_SIZE": SettingInfo(package="scrapy-zyte-api"),
    "ZYTE_API_SESSION_POOL_SIZES": SettingInfo(package="scrapy-zyte-api"),
    "ZYTE_API_SESSION_QUEUE_MAX_ATTEMPTS": SettingInfo(package="scrapy-zyte-api"),
    "ZYTE_API_SESSION_QUEUE_WAIT_TIME": SettingInfo(package="scrapy-zyte-api"),
    "ZYTE_API_SKIP_HEADERS": SettingInfo(package="scrapy-zyte-api"),
    "ZYTE_API_TRANSPARENT_MODE": SettingInfo(package="scrapy-zyte-api"),
    "ZYTE_API_USE_ENV_PROXY": SettingInfo(package="scrapy-zyte-api"),
    # scrapy-zyte-smartproxy plugin settings, in order of appearance in
    # https://scrapy-zyte-smartproxy.readthedocs.io/en/latest/settings.html
    "ZYTE_SMARTPROXY_APIKEY": SettingInfo(package="scrapy-zyte-smartproxy"),
    "ZYTE_SMARTPROXY_URL": SettingInfo(package="scrapy-zyte-smartproxy"),
    "ZYTE_SMARTPROXY_MAXBANS": SettingInfo(package="scrapy-zyte-smartproxy"),
    "ZYTE_SMARTPROXY_DOWNLOAD_TIMEOUT": SettingInfo(package="scrapy-zyte-smartproxy"),
    "ZYTE_SMARTPROXY_PRESERVE_DELAY": SettingInfo(package="scrapy-zyte-smartproxy"),
    "ZYTE_SMARTPROXY_DEFAULT_HEADERS": SettingInfo(package="scrapy-zyte-smartproxy"),
    "ZYTE_SMARTPROXY_BACKOFF_STEP": SettingInfo(package="scrapy-zyte-smartproxy"),
    "ZYTE_SMARTPROXY_BACKOFF_MAX": SettingInfo(package="scrapy-zyte-smartproxy"),
    "ZYTE_SMARTPROXY_FORCE_ENABLE_ON_HTTP_CODES": SettingInfo(
        package="scrapy-zyte-smartproxy"
    ),
    "ZYTE_SMARTPROXY_KEEP_HEADERS": SettingInfo(package="scrapy-zyte-smartproxy"),
}

HARDCODED_SUGGESTIONS = {
    "CONCURRENCY": ["CONCURRENT_REQUESTS", "CONCURRENT_REQUESTS_PER_DOMAIN"],
    "DELAY": ["DOWNLOAD_DELAY"],
}

MIN_SUGGESTION_SCORE = 0.6


def get_setting_suggestions(
    unknown_setting: str, known_settings: set[str], max_suggestions: int = 3
) -> list[str]:
    hardcoded = HARDCODED_SUGGESTIONS.get(unknown_setting.upper())
    if hardcoded:
        return hardcoded[:max_suggestions]

    return get_close_matches(
        unknown_setting.upper(),
        known_settings,
        n=max_suggestions,
        cutoff=MIN_SUGGESTION_SCORE,
    )


class BaseSettingsIssueFinder(IssueFinder, ABC):
    def __init__(self, filename=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.found_settings = set()
        self.filename = filename
        self.settings_methods = {
            "get": "name",
            "set": "name",
            "getbool": "name",
            "getint": "name",
            "getfloat": "name",
            "getlist": "name",
            "getdict": "name",
            "getdictorlist": "name",
            "getwithbase": "name",
            "getpriority": "name",
            "setdefault": "name",
            "delete": "name",
            "pop": "name",
        }

    @abstractmethod
    def should_report_setting(self, setting_name: str) -> bool:
        """Return True if this setting should be reported as an issue."""

    @abstractmethod
    def get_setting_message(self, setting_name: str) -> str:
        """Generate the message for this setting issue."""

    def find_issues(self, node) -> Generator[tuple[int, int, str], None, None]:
        if isinstance(node, ast.Assign):
            yield from self.check_assignment(node)
        elif isinstance(node, ast.Call):
            yield from self.check_call(node)
        elif isinstance(node, ast.Subscript):
            yield from self.check_subscript(node)
        elif isinstance(node, ast.Delete):
            yield from self.check_delete(node)
        for child in ast.iter_child_nodes(node):
            yield from self.find_issues(child)

    def check_assignment(
        self, node: ast.Assign
    ) -> Generator[tuple[int, int, str], None, None]:
        file_name = Path(self.filename).name if self.filename else None
        if file_name == "settings.py":
            for target in node.targets:
                if not isinstance(target, ast.Name) or not target.id.isupper():
                    continue
                setting_name = target.id
                if self.is_likely_setting(setting_name) and self.should_report_setting(
                    setting_name
                ):
                    yield from self.report_setting_issue(
                        node.lineno, node.col_offset, setting_name
                    )

        # Check for custom_settings assignments in any class
        if isinstance(node.value, ast.Dict):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "custom_settings":
                    yield from self.check_dict_keys(
                        node.value, node.lineno, node.col_offset
                    )

    def check_call(self, node: ast.Call) -> Generator[tuple[int, int, str], None, None]:  # noqa: PLR0911
        if isinstance(node.func, ast.Attribute):
            if self.is_settings_method_call(node):
                yield from self.check_settings_method_args(node)
                return
            if self.is_settings_dict_method_call(node):
                yield from self.check_settings_dict_method_args(node)
                return
            if node.func.attr != "overridden_settings":
                return
            if (
                isinstance(node.func.value, ast.Attribute)
                and node.func.value.attr == "settings"
                and isinstance(node.func.value.value, ast.Name)
                and node.func.value.value.id == "scrapy"
            ):
                yield from self.check_overridden_settings_args(node)
                return
            if (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "settings"
            ):
                yield from self.check_overridden_settings_args(node)
            return

        if not isinstance(node.func, ast.Name):
            return

        if node.func.id in {"BaseSettings", "Settings"}:
            yield from self.check_settings_constructor_args(node)
            return
        if node.func.id == "overridden_settings":
            yield from self.check_overridden_settings_args(node)

    def check_subscript(
        self, node: ast.Subscript
    ) -> Generator[tuple[int, int, str], None, None]:
        if not self.is_settings_subscript(node):
            return
        if not isinstance(node.slice, ast.Constant) or not isinstance(
            node.slice.value, str
        ):
            return
        setting_name = node.slice.value
        if self.should_report_setting(setting_name):
            yield from self.report_setting_issue(
                node.slice.lineno, node.slice.col_offset, setting_name
            )

    def check_dict_keys(
        self, dict_node: ast.Dict, line: int, col: int
    ) -> Generator[tuple[int, int, str], None, None]:
        for key in dict_node.keys:
            if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                continue
            setting_name = key.value
            if setting_name.isupper() and self.should_report_setting(setting_name):
                yield from self.report_setting_issue(
                    key.lineno, key.col_offset, setting_name
                )

    def check_dict_constructor_keywords(
        self, call_node: ast.Call
    ) -> Generator[tuple[int, int, str], None, None]:
        for keyword in call_node.keywords:
            if keyword.arg is None:
                continue
            setting_name = keyword.arg
            if setting_name.isupper() and self.should_report_setting(setting_name):
                keyword_col = keyword.value.col_offset - len(setting_name) - 1
                yield from self.report_setting_issue(
                    keyword.value.lineno, keyword_col, setting_name
                )

    def is_likely_setting(self, name: str) -> bool:
        return (
            name.isupper()
            and len(name) >= MIN_VALID_SETTING_NAME_LENGTH
            and not name.startswith("_")
        )

    def is_settings_method_call(self, node: ast.Call) -> bool:
        assert isinstance(node.func, ast.Attribute)
        method_name = node.func.attr
        if method_name not in self.settings_methods:
            return False
        return self.is_settings_object(node.func.value)

    def is_settings_dict_method_call(self, node: ast.Call) -> bool:
        assert isinstance(node.func, ast.Attribute)
        method_name = node.func.attr
        dict_methods = {"setdict", "update"}
        if method_name not in dict_methods:
            return False
        return self.is_settings_object(node.func.value)

    def is_settings_subscript(self, node: ast.Subscript) -> bool:
        return self.is_settings_object(node.value)

    def is_settings_object(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Name):
            return node.id == "settings"
        if not isinstance(node, ast.Attribute):
            return False
        return node.attr == "settings"

    def check_settings_method_args(
        self, node: ast.Call
    ) -> Generator[tuple[int, int, str], None, None]:
        assert isinstance(node.func, ast.Attribute)
        method_name = node.func.attr
        param_name = self.settings_methods[method_name]
        if node.args:
            first_arg = node.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                setting_name = first_arg.value
                if self.should_report_setting(setting_name):
                    yield from self.report_setting_issue(
                        first_arg.lineno, first_arg.col_offset, setting_name
                    )
        for keyword in node.keywords:
            if keyword.arg != param_name:
                continue
            if not isinstance(keyword.value, ast.Constant) or not isinstance(
                keyword.value.value, str
            ):
                continue
            setting_name = keyword.value.value
            if self.should_report_setting(setting_name):
                yield from self.report_setting_issue(
                    keyword.value.lineno, keyword.value.col_offset, setting_name
                )

    def check_settings_dict_method_args(
        self, node: ast.Call
    ) -> Generator[tuple[int, int, str], None, None]:
        if node.args:
            first_arg = node.args[0]
            if isinstance(first_arg, ast.Dict):
                yield from self.check_dict_keys(
                    first_arg, first_arg.lineno, first_arg.col_offset
                )
            elif (
                isinstance(first_arg, ast.Call)
                and isinstance(first_arg.func, ast.Name)
                and first_arg.func.id == "dict"
            ):
                yield from self.check_dict_constructor_keywords(first_arg)
        for keyword in node.keywords:
            if keyword.arg != "values":
                continue
            if isinstance(keyword.value, ast.Dict):
                yield from self.check_dict_keys(
                    keyword.value, keyword.value.lineno, keyword.value.col_offset
                )
            elif (
                isinstance(keyword.value, ast.Call)
                and isinstance(keyword.value.func, ast.Name)
                and keyword.value.func.id == "dict"
            ):
                yield from self.check_dict_constructor_keywords(keyword.value)

    def check_settings_constructor_args(
        self, node: ast.Call
    ) -> Generator[tuple[int, int, str], None, None]:
        for arg in node.args:
            if isinstance(arg, ast.Dict):
                yield from self.check_dict_keys(arg, arg.lineno, arg.col_offset)
            elif (
                isinstance(arg, ast.Call)
                and isinstance(arg.func, ast.Name)
                and arg.func.id == "dict"
            ):
                yield from self.check_dict_constructor_keywords(arg)
        for keyword in node.keywords:
            if keyword.arg != "values":
                continue
            if isinstance(keyword.value, ast.Dict):
                yield from self.check_dict_keys(
                    keyword.value, keyword.value.lineno, keyword.value.col_offset
                )
            elif (
                isinstance(keyword.value, ast.Call)
                and isinstance(keyword.value.func, ast.Name)
                and keyword.value.func.id == "dict"
            ):
                yield from self.check_dict_constructor_keywords(keyword.value)

    def check_overridden_settings_args(
        self, node: ast.Call
    ) -> Generator[tuple[int, int, str], None, None]:
        if node.args:
            first_arg = node.args[0]
            if isinstance(first_arg, ast.Dict):
                yield from self.check_dict_keys(
                    first_arg, first_arg.lineno, first_arg.col_offset
                )
        for keyword in node.keywords:
            if keyword.arg != "settings" or not isinstance(keyword.value, ast.Dict):
                continue
            yield from self.check_dict_keys(
                keyword.value, keyword.value.lineno, keyword.value.col_offset
            )

    def check_delete(
        self, node: ast.Delete
    ) -> Generator[tuple[int, int, str], None, None]:
        for target in node.targets:
            if not isinstance(target, ast.Subscript):
                continue
            if not self.is_settings_object(target.value):
                continue
            if not isinstance(target.slice, ast.Constant) or not isinstance(
                target.slice.value, str
            ):
                continue
            setting_name = target.slice.value
            if self.should_report_setting(setting_name):
                yield from self.report_setting_issue(
                    target.slice.lineno, target.slice.col_offset, setting_name
                )

    def report_setting_issue(
        self, line: int, col: int, setting_name: str
    ) -> Generator[tuple[int, int, str], None, None]:
        if setting_name in self.found_settings:
            return
        self.found_settings.add(setting_name)

        message = self.get_setting_message(setting_name)
        yield (line, col, message)

    def get_package_version(self, package_name) -> str | None:
        return self.package_versions.get(canonicalize_name(package_name), None)

    @property
    def package_versions(self) -> dict[str, str]:
        if hasattr(self, "_package_versions"):
            return self._package_versions
        self._package_versions = {}
        project_root = self.get_project_root()
        if not project_root:
            return self._package_versions
        requirements_txt = project_root / "requirements.txt"
        if not requirements_txt.exists():
            return self._package_versions
        try:
            requirements = requirements_txt.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return self._package_versions
        for line in requirements.splitlines():
            requirement = self.parse_requirement_line(line)
            if requirement is None:
                continue
            if not self.is_frozen_requirement(requirement):
                continue
            version = next(iter(requirement.specifier)).version
            self._package_versions[canonicalize_name(requirement.name)] = Version(
                version
            )
        return self._package_versions


class InvalidValueSettingsIssueFinder(
    BaseSettingsIssueFinder, AllowedExcludeSettingsMixin
):
    msg_code = "SCP18"
    msg_info = "invalid setting value"

    # Valid literal values for bool settings
    VALID_BOOL_LITERALS = (
        True,
        False,
        0,
        1,
        "True",
        "False",
        "true",
        "false",
        "0",
        "1",
    )

    # Valid types for bool settings when literal value cannot be determined
    VALID_BOOL_TYPES: ClassVar[set[type]] = {str, int, bool}

    # Valid literal values for log level settings
    VALID_LOG_LEVEL_LITERALS = (
        # String levels (case-insensitive)
        "CRITICAL",
        "FATAL",
        "ERROR",
        "WARNING",
        "WARN",
        "INFO",
        "DEBUG",
        "NOTSET",
        "critical",
        "fatal",
        "error",
        "warning",
        "warn",
        "info",
        "debug",
        "notset",
        # Standard numeric levels
        50,
        40,
        30,
        20,
        10,
        0,
    )

    def __init__(
        self,
        filename=None,
        allowed_settings=None,
        exclude_settings=None,
        *args,
        **kwargs,
    ):
        super().__init__(filename, *args, **kwargs)
        self.typed_settings = {}
        self.enum_settings = {}
        self._feeds_error_message = ""
        for name, info in SETTINGS.items():
            if info.type in (
                SettingType.BOOL,
                SettingType.INT,
                SettingType.FLOAT,
                SettingType.LIST,
                SettingType.DICT,
                SettingType.DICT_OR_LIST,
                SettingType.BASED_DICT,
                SettingType.OPT_STR,
                SettingType.STR,
                SettingType.CLS,
                SettingType.PATH,
                SettingType.OPT_PATH,
                SettingType.LOG_LEVEL,
                SettingType.ENUM_STR,
                SettingType.PERIODIC_LOG_CONFIG,
                SettingType.OPT_CALLABLE,
                SettingType.OPT_INT,
            ):
                self.typed_settings[name] = info.type
                if info.type == SettingType.ENUM_STR and info.allowed_values:
                    self.enum_settings[name] = info.allowed_values
        self._init_allowed_exclude_settings(allowed_settings, exclude_settings)
        self.validators = {
            SettingType.BOOL: lambda v: v in self.VALID_BOOL_LITERALS,
            SettingType.INT: self._can_convert_to_int,
            SettingType.FLOAT: self._can_convert_to_float,
            SettingType.LIST: self._can_convert_to_list,
            SettingType.DICT: self._can_convert_to_dict,
            SettingType.BASED_DICT: self._can_convert_to_dict,
            SettingType.DICT_OR_LIST: self._is_valid_dict_or_list_value,
            SettingType.OPT_STR: self._is_valid_optional_string,
            SettingType.STR: self._is_valid_string,
            SettingType.CLS: self._is_valid_class,
            SettingType.PATH: self._is_valid_path,
            SettingType.OPT_PATH: self._is_valid_optional_path,
            SettingType.LOG_LEVEL: self._is_valid_log_level,
            SettingType.ENUM_STR: self._is_valid_enum_string,
            SettingType.PERIODIC_LOG_CONFIG: self._is_valid_periodic_log_config,
            SettingType.OPT_CALLABLE: self._is_valid_optional_callable,
            SettingType.OPT_INT: self._is_valid_optional_int,
        }

        self.feeds_key_versions = {
            "batch_item_count": "2.3.0",
            "item_classes": "2.6.0",
            "item_filter": "2.6.0",
            "item_export_kwargs": "2.4.0",
            "overwrite": "2.4.0",
            "postprocessing": "2.6.0",
        }

    def should_report_setting(self, setting_name: str) -> bool:
        return (
            (
                setting_name in self.typed_settings
                or setting_name in ("USER_AGENT", "FEEDS", "DOWNLOAD_SLOTS")
            )
            and setting_name not in self.allowed_settings
            and setting_name not in self.exclude_settings
        )

    def get_setting_message(self, setting_name: str) -> str:
        if setting_name == "USER_AGENT":
            return (
                "SCP22: USER_AGENT does not seem to provide contact "
                "information. Put an URL, email address or phone number in it "
                "so that web masters of target websites may contact you."
            )

        if setting_name == "FEEDS":
            # This will be overridden by specific FEEDS error messages
            return (
                f"{self.msg_code}: {self.msg_info}: FEEDS {self._feeds_error_message}"
            )

        if setting_name == "DOWNLOAD_SLOTS":
            return f"{self.msg_code}: {self.msg_info}: DOWNLOAD_SLOTS {self._feeds_error_message}"

        setting_type = self.typed_settings[setting_name]

        type_messages = {
            SettingType.BOOL: f"only supports the following values: {', '.join(map(repr, self.VALID_BOOL_LITERALS))}.",
            SettingType.INT: "only supports values that can be passed to int()",
            SettingType.FLOAT: "only supports values that can be passed to float()",
            SettingType.LIST: "only supports values that can be passed to list()",
            SettingType.DICT: "only supports values that can be passed to dict() or strings defining a JSON object",
            SettingType.BASED_DICT: "only supports values that can be passed to dict() or strings defining a JSON object",
            SettingType.DICT_OR_LIST: "only supports None, str, tuple, dict, or list values",
            SettingType.OPT_STR: "only supports None or string values",
            SettingType.STR: "only supports string values",
            SettingType.CLS: "only supports class objects or strings containing class import paths",
            SettingType.PATH: "only supports Path objects or strings",
            SettingType.OPT_PATH: "only supports None, Path objects, or strings",
            SettingType.LOG_LEVEL: f"only supports valid logging levels: {', '.join(map(repr, self.VALID_LOG_LEVEL_LITERALS))} or any integer",
            SettingType.ENUM_STR: self._get_enum_message(setting_name),
            SettingType.PERIODIC_LOG_CONFIG: "only supports None, True, or a dict with 'include' and/or 'exclude' keys containing lists of strings",
            SettingType.OPT_CALLABLE: "only supports None, callable objects, or strings containing callable import paths",
            SettingType.OPT_INT: "only supports None or values that can be passed to int()",
        }

        message_suffix = type_messages.get(setting_type, "has an invalid value")
        return f"{self.msg_code}: {self.msg_info}: {setting_name} {message_suffix}"

    def check_assignment(
        self, node: ast.Assign
    ) -> Generator[tuple[int, int, str], None, None]:
        # Check direct assignments in settings.py
        file_name = Path(self.filename).name if self.filename else None
        if file_name == "settings.py":
            for target in node.targets:
                if not isinstance(target, ast.Name) or not target.id.isupper():
                    continue
                setting_name = target.id
                if self.should_report_setting(setting_name) and self._is_invalid_value(
                    node.value, setting_name
                ):
                    yield from self.report_setting_issue(
                        node.value.lineno, node.value.col_offset, setting_name
                    )

        # Check for custom_settings assignments in any class
        if isinstance(node.value, ast.Dict):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "custom_settings":
                    yield from self._check_dict_values(
                        node.value, node.lineno, node.col_offset
                    )

        # Check settings subscript assignments
        for target in node.targets:
            if (
                isinstance(target, ast.Subscript)
                and isinstance(target.ctx, ast.Store)
                and self.is_settings_subscript(target)
                and isinstance(target.slice, ast.Constant)
                and isinstance(target.slice.value, str)
            ):
                setting_name = target.slice.value
                if self.should_report_setting(setting_name) and self._is_invalid_value(
                    node.value, setting_name
                ):
                    yield from self.report_setting_issue(
                        node.value.lineno,
                        node.value.col_offset,
                        setting_name,
                    )

    def check_call(self, node: ast.Call) -> Generator[tuple[int, int, str], None, None]:  # noqa: PLR0912
        if not isinstance(node.func, ast.Attribute):
            return
        if not self.is_settings_object(node.func.value):
            return
        method_name = node.func.attr

        # Check settings.set() calls
        min_args_for_set = 2
        if method_name == "set":
            if (
                len(node.args) >= min_args_for_set
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                setting_name = node.args[0].value
                if self.should_report_setting(setting_name) and self._is_invalid_value(
                    node.args[1], setting_name
                ):
                    yield from self.report_setting_issue(
                        node.args[1].lineno,
                        node.args[1].col_offset,
                        setting_name,
                    )

            # Check keyword arguments
            for keyword in node.keywords:
                if (
                    keyword.arg == "name"
                    and isinstance(keyword.value, ast.Constant)
                    and self.should_report_setting(keyword.value.value)
                    and len(node.args) >= 1
                    and self._is_invalid_value(node.args[0], keyword.value.value)
                ):
                    setting_name = keyword.value.value
                    yield from self.report_setting_issue(
                        node.args[0].lineno,
                        node.args[0].col_offset,
                        setting_name,
                    )

        # Check settings.setdefault() calls
        elif method_name == "setdefault":
            if (
                len(node.args) >= min_args_for_set
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                setting_name = node.args[0].value
                if self.should_report_setting(setting_name) and self._is_invalid_value(
                    node.args[1], setting_name
                ):
                    yield from self.report_setting_issue(
                        node.args[1].lineno,
                        node.args[1].col_offset,
                        setting_name,
                    )

        # Check settings.setdict() calls
        elif method_name == "setdict":
            if node.args and isinstance(node.args[0], ast.Dict):
                yield from self._check_dict_values(
                    node.args[0], node.args[0].lineno, node.args[0].col_offset
                )

        # Check settings.update() calls
        elif method_name == "update":
            # Check dictionary argument
            if node.args and isinstance(node.args[0], ast.Dict):
                yield from self._check_dict_values(
                    node.args[0], node.args[0].lineno, node.args[0].col_offset
                )

            # Check keyword argument with dict value
            for keyword in node.keywords:
                if keyword.arg == "values" and isinstance(keyword.value, ast.Dict):
                    yield from self._check_dict_values(
                        keyword.value, keyword.value.lineno, keyword.value.col_offset
                    )

    def _check_dict_values(
        self, dict_node: ast.Dict, line: int, col: int
    ) -> Generator[tuple[int, int, str], None, None]:
        for key, value in zip(dict_node.keys, dict_node.values):
            if (
                isinstance(key, ast.Constant)
                and isinstance(key.value, str)
                and self.should_report_setting(key.value)
                and self._is_invalid_value(value, key.value)
            ):
                setting_name = key.value
                yield from self.report_setting_issue(
                    value.lineno, value.col_offset, setting_name
                )

    def _is_invalid_value(self, value_node: ast.AST, setting_name: str) -> bool:  # noqa: PLR0911
        if setting_name == "USER_AGENT":
            return self._is_invalid_user_agent(value_node)

        if setting_name == "FEEDS":
            feeds_error = self._get_feeds_validation_error(value_node)
            if feeds_error:
                self._feeds_error_message = feeds_error
                return True
            return False

        if setting_name == "DOWNLOAD_SLOTS":
            download_slots_error = self._get_download_slots_validation_error(value_node)
            if download_slots_error:
                self._feeds_error_message = download_slots_error
                return True
            return False

        setting_type = self.typed_settings[setting_name]

        # Special handling for enum string settings
        if setting_type == SettingType.ENUM_STR:
            return self._is_invalid_enum_value(value_node, setting_name)

        # Special handling for periodic log config settings
        if setting_type == SettingType.PERIODIC_LOG_CONFIG:
            return self._is_invalid_periodic_log_config_ast(value_node)

        # If we can identify the literal value
        if isinstance(value_node, ast.Constant):
            return self._is_invalid_constant_value(value_node.value, setting_type)

        # If we can identify the type but not the literal value
        if hasattr(value_node, "__class__"):
            return self._is_invalid_ast_node_type(value_node, setting_type)

        return False

    def _is_invalid_enum_value(self, value_node: ast.AST, setting_name: str) -> bool:
        if setting_name not in self.enum_settings:
            return False
        allowed_values = self.enum_settings[setting_name]
        if isinstance(value_node, ast.Constant):
            value = value_node.value
            if value is None:
                return True
            if not isinstance(value, str):
                return True
            return value not in allowed_values
        return isinstance(value_node, (ast.List, ast.Dict, ast.Set, ast.Tuple))

    def _is_invalid_constant_value(self, value, setting_type: SettingType) -> bool:
        if setting_type in self.validators:
            return not self.validators[setting_type](value)
        return False

    def _is_invalid_ast_node_type(
        self, value_node: ast.AST, setting_type: SettingType
    ) -> bool:
        complex_types = (ast.List, ast.Tuple, ast.Set, ast.Dict)
        if setting_type == SettingType.LIST:
            return False
        if setting_type in (SettingType.DICT, SettingType.BASED_DICT):
            return isinstance(value_node, (ast.List, ast.Tuple, ast.Set))
        if setting_type == SettingType.DICT_OR_LIST:
            return isinstance(value_node, ast.Set)
        if setting_type in (
            SettingType.STR,
            SettingType.OPT_STR,
            SettingType.CLS,
            SettingType.PATH,
            SettingType.OPT_PATH,
            SettingType.ENUM_STR,
            SettingType.OPT_CALLABLE,
            SettingType.OPT_INT,
        ):
            return isinstance(value_node, complex_types)
        return isinstance(value_node, complex_types)

    def _can_convert_to_int(self, value) -> bool:
        try:
            int(value)
            return True
        except (ValueError, TypeError):
            return False

    def _can_convert_to_float(self, value) -> bool:
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False

    def _can_convert_to_list(self, value) -> bool:
        try:
            list(value)
            return True
        except (ValueError, TypeError):
            return False

    def _can_convert_to_dict(self, value) -> bool:
        """Check if a value can be converted to dict or is a valid JSON object string."""
        # First try to convert to dict directly
        try:
            dict(value)
            return True
        except (ValueError, TypeError):
            pass

        # If it's a string, check if it's a valid JSON object (dict)
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return isinstance(parsed, dict)
            except (json.JSONDecodeError, ValueError):
                return False

        return False

    def _is_valid_dict_or_list_value(self, value) -> bool:
        if value is None:
            return True
        return isinstance(value, (str, tuple, dict, list))

    def _is_valid_optional_string(self, value) -> bool:
        return value is None or isinstance(value, str)

    def _is_valid_string(self, value) -> bool:
        return isinstance(value, str)

    def _is_valid_class(self, value) -> bool:
        if isinstance(value, type):
            return True
        if isinstance(value, str):
            return self._looks_like_class_import_path(value)
        return False

    def _looks_like_class_import_path(self, value: str) -> bool:
        if not value:
            return False
        parts = value.split(".")
        MINIMUM_IMPORT_PARTS = 2
        if len(parts) < MINIMUM_IMPORT_PARTS:
            return False
        for part in parts:
            if not part.isidentifier():
                return False
        return parts[-1][0].isupper()

    def _looks_like_callable_import_path(self, value: str) -> bool:
        """Check if a string looks like a valid import path for any callable (function, class, etc.)."""
        if not value:
            return False
        parts = value.split(".")
        MINIMUM_IMPORT_PARTS = 2
        if len(parts) < MINIMUM_IMPORT_PARTS:
            return False
        return all(part.isidentifier() for part in parts)

    def _is_valid_path(self, value) -> bool:
        if isinstance(value, Path):
            return True
        return isinstance(value, str)

    def _is_valid_optional_path(self, value) -> bool:
        if value is None:
            return True
        return self._is_valid_path(value)

    def _is_valid_log_level(self, value) -> bool:
        """Check if a value is a valid logging level."""
        # Accept any integer (logging accepts any integer level)
        if isinstance(value, int):
            return True

        # Accept valid string logging level names (case-insensitive)
        if isinstance(value, str):
            return value.upper() in {
                "CRITICAL",
                "FATAL",
                "ERROR",
                "WARNING",
                "WARN",
                "INFO",
                "DEBUG",
                "NOTSET",
            }

        # Reject None and other types
        return False

    def _is_valid_enum_string(self, value) -> bool:
        return isinstance(value, str)

    def _is_valid_periodic_log_config(self, value) -> bool:  # noqa: PLR0911
        """Check if a value is valid for PERIODIC_LOG_DELTA or PERIODIC_LOG_STATS."""
        # Allow None
        if value is None:
            return True

        # Allow True (but not False or other boolean values)
        if value is True:
            return True

        # Allow dict with only 'include' and/or 'exclude' keys
        if isinstance(value, dict):
            # Check that only 'include' and/or 'exclude' keys are present
            allowed_keys = {"include", "exclude"}
            if not set(value.keys()).issubset(allowed_keys):
                return False

            # Check that values are lists of strings
            for val in value.values():
                if not isinstance(val, list):
                    return False
                if not all(isinstance(item, str) for item in val):
                    return False

            return True

        return False

    def _is_valid_optional_callable(self, value) -> bool:
        """Check if a value is valid for OPT_CALLABLE type settings."""
        if value is None:
            return True
        if callable(value):
            return True
        if isinstance(value, str):
            return self._looks_like_callable_import_path(value)
        return False

    def _is_valid_optional_int(self, value) -> bool:
        """Check if a value is valid for OPT_INT type settings."""
        if value is None:
            return True
        return self._can_convert_to_int(value)

    def _is_invalid_periodic_log_config_ast(self, value_node: ast.AST) -> bool:  # noqa: PLR0911
        """Check if an AST node is invalid for PERIODIC_LOG_DELTA or PERIODIC_LOG_STATS."""
        # Handle constants (None, True, False, strings, etc.)
        if isinstance(value_node, ast.Constant):
            return not self._is_valid_periodic_log_config(value_node.value)

        # Handle dictionaries
        if isinstance(value_node, ast.Dict):
            # Check that only 'include' and/or 'exclude' keys are present
            allowed_keys = {"include", "exclude"}
            for key_node in value_node.keys:
                if not isinstance(key_node, ast.Constant) or not isinstance(
                    key_node.value, str
                ):
                    return True  # Invalid key type
                if key_node.value not in allowed_keys:
                    return True  # Invalid key name

            # Check that values are lists
            for value_node_item in value_node.values:
                if not isinstance(value_node_item, ast.List):
                    return True  # Value is not a list

                # Check that list items are strings
                for list_item in value_node_item.elts:
                    if not isinstance(list_item, ast.Constant) or not isinstance(
                        list_item.value, str
                    ):
                        return True  # List item is not a string

            return False  # Valid dict

        # All other types are invalid
        return True

    def _get_enum_message(self, setting_name: str) -> str:
        if setting_name in self.enum_settings:
            allowed_values = ", ".join(
                f"'{v}'" for v in self.enum_settings[setting_name]
            )
            return f"only supports the following values: {allowed_values}."
        return "only supports specific string values."

    def _is_invalid_user_agent(self, value_node: ast.AST) -> bool:
        if not isinstance(value_node, ast.Constant):
            return isinstance(
                value_node, (ast.Num, ast.List, ast.Dict, ast.Set, ast.Tuple)
            )
        value = value_node.value
        if not isinstance(value, str):
            return True
        if not value:
            return True
        if "(+http://www.yourdomain.com)" in value or "(+https://scrapy.org)" in value:
            return True
        browser_patterns = [
            r"Mozilla/\d+\.\d+",
            r"Chrome/\d+\.\d+",
            r"Safari/\d+\.\d+",
            r"Firefox/\d+\.\d+",
            r"AppleWebKit/\d+\.\d+",
            r"Gecko/\d+",
        ]
        for pattern in browser_patterns:
            if re.search(pattern, value):
                return True
        url_pattern = (
            r"https?://[a-zA-Z0-9.-]+|www\.[a-zA-Z0-9.-]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        )
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        phone_pattern = r"\b\d{3}[-.]\d{4}\b|\b\d{10,}\b|\b\(\d{3}\)\s?\d{3}[-.]\d{4}\b"
        return not (
            re.search(url_pattern, value)
            or re.search(email_pattern, value)
            or re.search(phone_pattern, value)
        )

    def _get_feeds_validation_error(self, value_node: ast.AST) -> str:  # noqa: PLR0911
        """Get specific validation error for FEEDS setting, or empty string if valid."""
        # FEEDS must be a dict
        if isinstance(value_node, ast.Constant):
            value = value_node.value
            if isinstance(value, dict):
                return self._get_feeds_dict_validation_error(value)
            if isinstance(value, str):
                try:
                    parsed_value = json.loads(value)
                    if not isinstance(parsed_value, dict):
                        return "must be a dict"
                    return self._get_feeds_dict_validation_error(parsed_value)
                except (json.JSONDecodeError, TypeError):
                    return "must be a dict"
            else:
                return "must be a dict"

        if isinstance(value_node, ast.Dict):
            return self._get_feeds_dict_ast_validation_error(value_node)

        # Any other AST node type is invalid for FEEDS
        return "must be a dict"

    def _get_feeds_dict_validation_error(self, feeds_dict: dict) -> str:
        """Get validation error for a FEEDS dict value at runtime."""
        for key, feed_config in feeds_dict.items():
            # Root keys may be strings or Path objects
            if not isinstance(key, (str, Path)):
                return f"key {key!r} must be a string or Path object"

            # Feed config must be a dict
            if not isinstance(feed_config, dict):
                return f"feed config for {key!r} must be a dict"

            # Validate feed config keys and values
            error = self._get_feed_config_validation_error(key, feed_config)
            if error:
                return error

        return ""

    def _get_feeds_dict_ast_validation_error(self, dict_node: ast.Dict) -> str:
        """Get validation error for a FEEDS dict AST node."""
        for key_node, value_node in zip(dict_node.keys, dict_node.values):
            # Root keys may be strings or Path objects
            key_repr = "<?>"
            if isinstance(key_node, ast.Constant):
                key_repr = repr(key_node.value)
                if not isinstance(key_node.value, str):
                    return f"key {key_repr} must be a string or Path object"
            elif not (
                isinstance(key_node, ast.Call)
                and isinstance(key_node.func, ast.Name)
                and key_node.func.id == "Path"
            ):
                # Not a string constant or Path() call
                return f"key {key_repr} must be a string or Path object"

            # Feed config must be a dict
            if not isinstance(value_node, ast.Dict):
                # Check if this looks like feed config keys were used at the top level
                if isinstance(key_node, ast.Constant) and isinstance(
                    key_node.value, str
                ):
                    feed_config_keys = {
                        "format",
                        "batch_item_count",
                        "encoding",
                        "fields",
                        "item_classes",
                        "item_filter",
                        "indent",
                        "item_export_kwargs",
                        "overwrite",
                        "store_empty",
                        "uri_params",
                        "postprocessing",
                    }
                    if key_node.value in feed_config_keys:
                        return f"missing feed URL: {key_repr} appears to be a feed configuration key, but FEEDS must be a dict where keys are feed URLs (like 'output.json') and values are feed configurations"
                return f"feed config for {key_repr} must be a dict"

            # Validate feed config AST
            error = self._get_feed_config_ast_validation_error(key_repr, value_node)
            if error:
                return error

        return ""

    def _get_feed_config_validation_error(  # noqa: PLR0911, PLR0912
        self, feed_key: str, feed_config: dict
    ) -> str:
        """Get validation error for a feed config dict value."""
        for key, value in feed_config.items():
            # Feed config keys must be strings
            if not isinstance(key, str):
                return f"feed config key {key!r} in {feed_key!r} must be a string"

            # Check if this is a future key for the current Scrapy version
            if key in self.feeds_key_versions:
                required_version = self.feeds_key_versions[key]
                scrapy_version = self.get_package_version("scrapy")
                if (
                    scrapy_version is not None
                    and Version(required_version) > scrapy_version
                ):
                    return f"'{key}' in {feed_key!r} is not available in Scrapy {scrapy_version}, requires Scrapy {required_version} or later"

            # Validate specific feed config keys
            if key == "format" and not isinstance(value, str):
                return f"'format' in {feed_key!r} must be a string"
            if key == "batch_item_count" and not (
                isinstance(value, int) and value >= 0
            ):
                return (
                    f"'batch_item_count' in {feed_key!r} must be a non-negative integer"
                )
            if key == "encoding" and value is not None and not isinstance(value, str):
                return f"'encoding' in {feed_key!r} must be a string or None"
            if key == "fields":
                if value is not None:
                    if isinstance(value, list):
                        if not all(isinstance(item, str) for item in value):
                            return f"'fields' in {feed_key!r} must be None, a list of strings, or a dict mapping strings to strings"
                    elif isinstance(value, dict):
                        if not all(
                            isinstance(k, str) and isinstance(v, str)
                            for k, v in value.items()
                        ):
                            return f"'fields' in {feed_key!r} must be None, a list of strings, or a dict mapping strings to strings"
                    else:
                        return f"'fields' in {feed_key!r} must be None, a list of strings, or a dict mapping strings to strings"
            elif key in ("item_classes", "postprocessing"):
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            if not self._looks_like_class_import_path(item):
                                return f"'{key}' in {feed_key!r} contains invalid import path {item!r}"
                        elif not isinstance(item, type):
                            return f"'{key}' in {feed_key!r} must be a list of class objects or class import path strings"
                else:
                    return f"'{key}' in {feed_key!r} must be a list of class objects or class import path strings"
            elif key == "item_filter":
                if isinstance(value, str):
                    if not self._looks_like_class_import_path(value):
                        return f"'item_filter' in {feed_key!r} contains invalid import path {value!r}"
                elif not isinstance(value, type):
                    return f"'item_filter' in {feed_key!r} must be a class object or class import path string"
            elif key == "indent" and not (isinstance(value, int) and value >= 0):
                return f"'indent' in {feed_key!r} must be a non-negative integer"
            elif key == "item_export_kwargs" and not isinstance(value, dict):
                return f"'item_export_kwargs' in {feed_key!r} must be a dict"
            elif key == "overwrite" and not isinstance(value, bool):
                return f"'overwrite' in {feed_key!r} must be a boolean"
            elif key == "store_empty" and not isinstance(value, bool):
                return f"'store_empty' in {feed_key!r} must be a boolean"
            elif key == "uri_params":
                if isinstance(value, str):
                    if not self._looks_like_callable_import_path(value):
                        return f"'uri_params' in {feed_key!r} contains invalid callable import path {value!r}"
                elif not callable(value):
                    return f"'uri_params' in {feed_key!r} must be a callable or callable import path string"

        return ""

    def _get_feed_config_ast_validation_error(  # noqa: PLR0911, PLR0912
        self, feed_key: str, dict_node: ast.Dict
    ) -> str:
        """Get validation error for a feed config dict AST node."""
        for key_node, value_node in zip(dict_node.keys, dict_node.values):
            # Feed config keys must be strings
            if not isinstance(key_node, ast.Constant) or not isinstance(
                key_node.value, str
            ):
                return f"feed config key in {feed_key} must be a string"

            key = key_node.value

            # Check if this is a future key for the current Scrapy version
            if key in self.feeds_key_versions:
                required_version = self.feeds_key_versions[key]
                scrapy_version = self.get_package_version("scrapy")
                if (
                    scrapy_version is not None
                    and Version(required_version) > scrapy_version
                ):
                    return f"'{key}' in {feed_key} is not available in Scrapy {scrapy_version}, requires Scrapy {required_version} or later"

            # Validate specific feed config keys
            if key == "format":
                if not (
                    isinstance(value_node, ast.Constant)
                    and isinstance(value_node.value, str)
                ):
                    return f"'format' in {feed_key} must be a string"
            elif key == "batch_item_count":
                if not (
                    isinstance(value_node, ast.Constant)
                    and isinstance(value_node.value, int)
                    and value_node.value >= 0
                ):
                    return f"'batch_item_count' in {feed_key} must be a non-negative integer"
            elif key == "encoding":
                if not (
                    isinstance(value_node, ast.Constant)
                    and (value_node.value is None or isinstance(value_node.value, str))
                ):
                    return f"'encoding' in {feed_key} must be a string or None"
            elif key == "fields":
                if isinstance(value_node, ast.Constant):
                    if value_node.value is not None:
                        return f"'fields' in {feed_key} must be None, a list of strings, or a dict mapping strings to strings"
                elif isinstance(value_node, ast.List):
                    # List of strings
                    for item in value_node.elts:
                        if not (
                            isinstance(item, ast.Constant)
                            and isinstance(item.value, str)
                        ):
                            return f"'fields' in {feed_key} must be None, a list of strings, or a dict mapping strings to strings"
                elif isinstance(value_node, ast.Dict):
                    # Dict[str, str]
                    for k, v in zip(value_node.keys, value_node.values):
                        if not (
                            isinstance(k, ast.Constant)
                            and isinstance(k.value, str)
                            and isinstance(v, ast.Constant)
                            and isinstance(v.value, str)
                        ):
                            return f"'fields' in {feed_key} must be None, a list of strings, or a dict mapping strings to strings"
                else:
                    return f"'fields' in {feed_key} must be None, a list of strings, or a dict mapping strings to strings"
            elif key in ("item_classes", "postprocessing"):
                if isinstance(value_node, ast.List):
                    for item in value_node.elts:
                        if isinstance(item, ast.Constant) and not (
                            isinstance(item.value, str)
                            and self._looks_like_class_import_path(item.value)
                        ):
                            return f"'{key}' in {feed_key} contains invalid import path {item.value!r}"
                        # Allow any other AST node type for class references (Name, Attribute, etc.)
                else:
                    return f"'{key}' in {feed_key} must be a list of class objects or class import path strings"
            elif key == "item_filter":
                if isinstance(value_node, ast.Constant) and not (
                    isinstance(value_node.value, str)
                    and self._looks_like_class_import_path(value_node.value)
                ):
                    return f"'item_filter' in {feed_key} contains invalid import path {value_node.value!r}"
                # Allow any other AST node type for class references (Name, Attribute, etc.)
            elif key == "indent":
                if not (
                    isinstance(value_node, ast.Constant)
                    and isinstance(value_node.value, int)
                    and value_node.value >= 0
                ):
                    return f"'indent' in {feed_key} must be a non-negative integer"
            elif key == "item_export_kwargs":
                if not isinstance(value_node, ast.Dict):
                    return f"'item_export_kwargs' in {feed_key} must be a dict"
            elif key in ("overwrite", "store_empty"):
                if not (
                    isinstance(value_node, ast.Constant)
                    and isinstance(value_node.value, bool)
                ):
                    return f"'{key}' in {feed_key} must be a boolean"
            elif (
                key == "uri_params"
                and isinstance(value_node, ast.Constant)
                and not (
                    isinstance(value_node.value, str)
                    and self._looks_like_callable_import_path(value_node.value)
                )
            ):
                return f"'uri_params' in {feed_key} contains invalid callable import path {value_node.value!r}"
            # Allow any other AST node type for callable references (Name, Attribute, etc.)

        return ""

    def _get_download_slots_validation_error(self, value_node: ast.AST) -> str:  # noqa: PLR0911
        if isinstance(value_node, ast.Constant):
            value = value_node.value
            if isinstance(value, dict):
                return self._get_download_slots_dict_validation_error(value)
            if isinstance(value, str):
                try:
                    parsed_value = json.loads(value)
                    if not isinstance(parsed_value, dict):
                        return "must be a dict"
                    return self._get_download_slots_dict_validation_error(parsed_value)
                except (json.JSONDecodeError, TypeError):
                    return "must be a dict"
            else:
                return "must be a dict"

        if isinstance(value_node, ast.Dict):
            return self._get_download_slots_dict_ast_validation_error(value_node)

        return "must be a dict"

    def _get_download_slots_dict_validation_error(self, slots_dict: dict) -> str:
        for key, slot_config in slots_dict.items():
            if not isinstance(key, str):
                return f"key {key!r} must be a string"

            if not isinstance(slot_config, dict):
                return f"slot config for {key!r} must be a dict"

            error = self._get_slot_config_validation_error(key, slot_config)
            if error:
                return error

        return ""

    def _get_download_slots_dict_ast_validation_error(self, dict_node: ast.Dict) -> str:
        for key_node, value_node in zip(dict_node.keys, dict_node.values):
            key_repr = "<?>"
            if isinstance(key_node, ast.Constant):
                key_repr = repr(key_node.value)
                if not isinstance(key_node.value, str):
                    return f"key {key_repr} must be a string"
            else:
                return f"key {key_repr} must be a string"

            if not isinstance(value_node, ast.Dict):
                return f"slot config for {key_repr} must be a dict"

            error = self._get_slot_config_ast_validation_error(key_repr, value_node)
            if error:
                return error

        return ""

    def _get_slot_config_validation_error(
        self, slot_key: str, slot_config: dict
    ) -> str:
        allowed_keys = {"concurrency", "delay", "randomize_delay"}
        for key, value in slot_config.items():
            if not isinstance(key, str):
                return f"slot config key {key!r} in {slot_key!r} must be a string"

            if key not in allowed_keys:
                return f"unknown slot config key '{key}' in {slot_key!r}, must be one of: {', '.join(sorted(allowed_keys))}"

            if key == "concurrency" and not (isinstance(value, int) and value >= 1):
                return f"'concurrency' in {slot_key!r} must be a positive integer (1+)"
            if key == "delay" and not (
                isinstance(value, (int, float)) and value >= 0.0
            ):
                return f"'delay' in {slot_key!r} must be a positive float (0.0+)"
            if key == "randomize_delay" and not isinstance(value, bool):
                return f"'randomize_delay' in {slot_key!r} must be a boolean"

        return ""

    def _get_slot_config_ast_validation_error(
        self, slot_key: str, dict_node: ast.Dict
    ) -> str:
        allowed_keys = {"concurrency", "delay", "randomize_delay"}
        for key_node, value_node in zip(dict_node.keys, dict_node.values):
            if not isinstance(key_node, ast.Constant) or not isinstance(
                key_node.value, str
            ):
                return f"slot config key in {slot_key} must be a string"

            key = key_node.value

            if key not in allowed_keys:
                return f"unknown slot config key '{key}' in {slot_key}, must be one of: {', '.join(sorted(allowed_keys))}"

            if key == "concurrency":
                if not (
                    isinstance(value_node, ast.Constant)
                    and isinstance(value_node.value, int)
                    and value_node.value >= 1
                ):
                    return (
                        f"'concurrency' in {slot_key} must be a positive integer (1+)"
                    )
            elif key == "delay":
                if not (
                    isinstance(value_node, ast.Constant)
                    and isinstance(value_node.value, (int, float))
                    and value_node.value >= 0.0
                ):
                    return f"'delay' in {slot_key} must be a positive float (0.0+)"
            elif key == "randomize_delay" and not (
                isinstance(value_node, ast.Constant)
                and isinstance(value_node.value, bool)
            ):
                return f"'randomize_delay' in {slot_key} must be a boolean"

        return ""

    def check_subscript(
        self, node: ast.Subscript
    ) -> Generator[tuple[int, int, str], None, None]:
        # SCP18 only cares about assignments, not subscript reads
        # So we override this method to do nothing for subscript operations
        return
        yield  # unreachable, but needed to make this a generator


class UnknownSettingsIssueFinder(BaseSettingsIssueFinder):
    msg_code = "SCP07"
    msg_info = "unknown Scrapy setting"

    def __init__(
        self,
        filename=None,
        allowed_settings=None,
        exclude_settings=None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, filename=filename, **kwargs)
        self.known_settings = set(SETTINGS)
        if allowed_settings:
            self.known_settings.update(allowed_settings)
        self.exclude_settings = set(exclude_settings) if exclude_settings else set()

    def should_report_setting(self, setting_name: str) -> bool:
        return (
            setting_name not in self.known_settings
            and setting_name not in self.exclude_settings
        )

    def get_setting_message(self, setting_name: str) -> str:
        suggestions = get_setting_suggestions(setting_name, self.known_settings)
        message = f"{self.msg_code}: {self.msg_info}: {setting_name}"

        if not suggestions:
            return message

        if len(suggestions) == 1:
            message += f". Did you mean {suggestions[0]}?"
        else:
            suggestion_list = ", ".join(suggestions)
            message += f". Did you mean one of: {suggestion_list}?"

        return message


class DeprecatedSettingsIssueFinder(
    BaseSettingsIssueFinder, AllowedExcludeSettingsMixin
):
    msg_code = "SCP08"
    msg_info = "deprecated Scrapy setting"

    def __init__(
        self,
        filename=None,
        allowed_settings=None,
        exclude_settings=None,
        *args,
        **kwargs,
    ):
        super().__init__(filename, *args, **kwargs)
        self.deprecated_settings = self.get_deprecated_settings()
        self._init_allowed_exclude_settings(allowed_settings, exclude_settings)

    def get_deprecated_settings(self) -> set[str]:
        deprecated = set()
        for name, info in SETTINGS.items():
            package_version = self.get_package_version(info.package)
            if package_version is None:
                continue
            if (
                info.removed_version
                and Version(info.removed_version) <= package_version
            ):
                continue
            if info.added_version and Version(info.added_version) > package_version:
                continue
            if (
                info.deprecated_version
                and Version(info.deprecated_version) <= package_version
            ):
                deprecated.add(name)
        return deprecated

    def should_report_setting(self, setting_name: str) -> bool:
        return (
            setting_name in self.deprecated_settings
            and setting_name not in self.allowed_settings
            and setting_name not in self.exclude_settings
        )

    def get_setting_message(self, setting_name: str) -> str:
        setting_info = SETTINGS[setting_name]
        version = setting_info.deprecated_version
        package = setting_info.package
        if package == "scrapy" and version == MINIMUM_SUPPORTED_SCRAPY_VERSION:
            version = f"{MINIMUM_SUPPORTED_SCRAPY_VERSION} or earlier"
        package_name = "Scrapy" if package == "scrapy" else package
        if package == "scrapy":
            message = f"{self.msg_code}: {self.msg_info}: {setting_name} (deprecated in {package_name} {version})"
        else:
            message = f"{self.msg_code}: deprecated setting: {setting_name} (deprecated in {package_name} {version})"
        deprecation_message = setting_info.deprecation_message
        if deprecation_message:
            message += f". {deprecation_message}"
        return message


class FutureSettingsIssueFinder(BaseSettingsIssueFinder, AllowedExcludeSettingsMixin):
    msg_code = "SCP09"
    msg_info = "future Scrapy setting"

    def __init__(
        self,
        filename=None,
        allowed_settings=None,
        exclude_settings=None,
        *args,
        **kwargs,
    ):
        super().__init__(filename, *args, **kwargs)
        self.future_settings = set()
        for name, info in SETTINGS.items():
            if not info.added_version:
                continue
            package_version = self.get_package_version(info.package)
            if (
                package_version is not None
                and Version(info.added_version) > package_version
            ):
                self.future_settings.add(name)
        self._init_allowed_exclude_settings(allowed_settings, exclude_settings)

    def should_report_setting(self, setting_name: str) -> bool:
        return (
            setting_name in self.future_settings
            and setting_name not in self.allowed_settings
            and setting_name not in self.exclude_settings
        )

    def get_setting_message(self, setting_name: str) -> str:
        setting_info = SETTINGS[setting_name]
        version = setting_info.added_version
        package = setting_info.package
        package_name = "Scrapy" if package == "scrapy" else package
        return f"{self.msg_code}: {self.msg_info}: {setting_name} (added in {package_name} {version})"


class RemovedSettingsIssueFinder(BaseSettingsIssueFinder, AllowedExcludeSettingsMixin):
    msg_code = "SCP10"
    msg_info = "removed Scrapy setting"

    def __init__(
        self,
        filename=None,
        allowed_settings=None,
        exclude_settings=None,
        *args,
        **kwargs,
    ):
        super().__init__(filename, *args, **kwargs)
        self.removed_settings = set()
        for name, info in SETTINGS.items():
            if not info.removed_version:
                continue
            package_version = self.get_package_version(info.package)
            if (
                package_version is not None
                and Version(info.removed_version) <= package_version
            ):
                self.removed_settings.add(name)
        self._init_allowed_exclude_settings(allowed_settings, exclude_settings)

    def should_report_setting(self, setting_name: str) -> bool:
        return (
            setting_name in self.removed_settings
            and setting_name not in self.allowed_settings
            and setting_name not in self.exclude_settings
        )

    def get_setting_message(self, setting_name: str) -> str:
        setting_info = SETTINGS[setting_name]
        version = setting_info.removed_version
        package = setting_info.package
        package_name = "Scrapy" if package == "scrapy" else package
        return f"{self.msg_code}: {self.msg_info}: {setting_name} (removed in {package_name} {version})"


class MissingPackageSettingsIssueFinder(
    BaseSettingsIssueFinder, AllowedExcludeSettingsMixin
):
    msg_code = "SCP15"
    msg_info = "setting for package not in requirements.txt"

    def __init__(self, filename=None, allowed_settings=None, *args, **kwargs):
        super().__init__(filename, *args, **kwargs)
        self.missing_package_settings = set()
        for name, info in SETTINGS.items():
            if (
                info.package != "scrapy"
                and self.get_package_version(info.package) is None
            ):
                self.missing_package_settings.add(name)
        self._init_allowed_exclude_settings(allowed_settings)

    def should_report_setting(self, setting_name: str) -> bool:
        return (
            setting_name in self.missing_package_settings
            and setting_name not in self.allowed_settings
        )

    def get_setting_message(self, setting_name: str) -> str:
        setting_info = SETTINGS[setting_name]
        package = setting_info.package
        return f"{self.msg_code}: {self.msg_info}: {setting_name} (package: {package})"


class TypeMismatchSettingsIssueFinder(
    BaseSettingsIssueFinder, AllowedExcludeSettingsMixin
):
    msg_code = "SCP17"
    msg_info = "wrong setting getter"

    TYPE_TO_METHOD: ClassVar[dict[SettingType, str]] = {
        SettingType.BOOL: "getbool",
        SettingType.INT: "getint",
        SettingType.FLOAT: "getfloat",
        SettingType.LIST: "getlist",
        SettingType.DICT: "getdict",
        SettingType.DICT_OR_LIST: "getdictorlist",
        SettingType.BASED_DICT: "getwithbase",
    }

    def __init__(
        self,
        filename=None,
        allowed_settings=None,
        exclude_settings=None,
        *args,
        **kwargs,
    ):
        super().__init__(filename, *args, **kwargs)
        self.typed_settings = {}
        for name, info in SETTINGS.items():
            if info.type is not None:
                self.typed_settings[name] = info.type
        self._init_allowed_exclude_settings(allowed_settings, exclude_settings)

    def should_report_setting(self, setting_name: str) -> bool:
        return (
            setting_name in self.typed_settings
            and setting_name not in self.allowed_settings
            and setting_name not in self.exclude_settings
        )

    def get_setting_message(self, setting_name: str) -> str:
        setting_type = self.typed_settings[setting_name]
        expected_method = self.TYPE_TO_METHOD.get(setting_type, "get")
        if expected_method == "get":
            return f"{self.msg_code}: {self.msg_info}: use [] or get() to read {setting_name}"
        return f"{self.msg_code}: {self.msg_info}: use {expected_method}() to read {setting_name}"

    def check_settings_method_args(
        self, node: ast.Call
    ) -> Generator[tuple[int, int, str], None, None]:
        assert isinstance(node.func, ast.Attribute)
        method_name = node.func.attr
        param_name = self.settings_methods[method_name]
        if node.args:
            first_arg = node.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                setting_name = first_arg.value
                if (
                    self.should_report_setting(setting_name)
                    and setting_name in self.typed_settings
                ):
                    setting_type = self.typed_settings[setting_name]
                    expected_method = self.TYPE_TO_METHOD.get(setting_type, "get")
                    if method_name != expected_method:
                        yield from self.report_setting_issue(
                            first_arg.lineno, first_arg.col_offset, setting_name
                        )
        for keyword in node.keywords:
            if keyword.arg != param_name:
                continue
            if not isinstance(keyword.value, ast.Constant) or not isinstance(
                keyword.value.value, str
            ):
                continue
            setting_name = keyword.value.value
            if (
                self.should_report_setting(setting_name)
                and setting_name in self.typed_settings
            ):
                setting_type = self.typed_settings[setting_name]
                expected_method = self.TYPE_TO_METHOD.get(setting_type, "get")
                if method_name != expected_method:
                    yield from self.report_setting_issue(
                        keyword.value.lineno, keyword.value.col_offset, setting_name
                    )

    def check_assignment(
        self, node: ast.Assign
    ) -> Generator[tuple[int, int, str], None, None]:
        # SCP17 only cares about reading settings, not assignments
        # So we override this method to do nothing for assignment operations
        return
        yield  # unreachable, but needed to make this a generator

    def check_call(self, node: ast.Call) -> Generator[tuple[int, int, str], None, None]:
        if not isinstance(node.func, ast.Attribute):
            return
        if not self.is_settings_object(node.func.value):
            return

        method_name = node.func.attr

        # Only check getter methods, not setter methods
        getter_methods = {
            "get",
            "getbool",
            "getint",
            "getfloat",
            "getlist",
            "getdict",
            "getdictorlist",
            "getwithbase",
            "getpriority",
        }

        if method_name not in getter_methods:
            return

        # Use the original settings method checking logic
        if self.is_settings_method_call(node):
            yield from self.check_settings_method_args(node)

    def check_subscript(
        self, node: ast.Subscript
    ) -> Generator[tuple[int, int, str], None, None]:
        if not isinstance(node.ctx, ast.Load):
            return
        if not self.is_settings_subscript(node):
            return
        if not isinstance(node.slice, ast.Constant) or not isinstance(
            node.slice.value, str
        ):
            return
        setting_name = node.slice.value
        if self.should_report_setting(setting_name):
            yield from self.report_setting_issue(
                node.slice.lineno, node.slice.col_offset, setting_name
            )


class MissingUserAgentIssueFinder(IssueFinder):
    msg_code = "SCP19"
    msg_info = "missing USER_AGENT setting"

    def __init__(self, filename=None, *args, **kwargs):
        super().__init__(filename, *args, **kwargs)
        self.found_user_agent = False

    def find_issues(self, node) -> Generator[tuple[int, int, str], None, None]:
        file_name = Path(self.filename).name if self.filename else None
        if file_name != "settings.py":
            return

        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "USER_AGENT":
                    self.found_user_agent = True

        if isinstance(node, ast.Module):
            # Traverse all child nodes first to check for USER_AGENT
            for child in ast.walk(node):
                if isinstance(child, ast.Assign):
                    for target in child.targets:
                        if isinstance(target, ast.Name) and target.id == "USER_AGENT":
                            self.found_user_agent = True
                            break

            if not self.found_user_agent:
                yield (1, 0, f"{self.msg_code}: No USER_AGENT in settings.py")


class RobotsTxtObeyIssueFinder(IssueFinder):
    msg_code = "SCP20"
    msg_info = "ROBOTSTXT_OBEY not enabled"

    def __init__(self, filename=None, *args, **kwargs):
        super().__init__(filename, *args, **kwargs)
        self.found_robotstxt_obey = False
        self.robotstxt_obey_enabled = False

    def find_issues(self, node) -> Generator[tuple[int, int, str], None, None]:
        file_name = Path(self.filename).name if self.filename else None
        if file_name != "settings.py":
            return

        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "ROBOTSTXT_OBEY":
                    self.found_robotstxt_obey = True
                    if (
                        isinstance(node.value, ast.Constant)
                        and node.value.value is True
                    ):
                        self.robotstxt_obey_enabled = True

        if isinstance(node, ast.Module):
            for child in ast.walk(node):
                if isinstance(child, ast.Assign):
                    for target in child.targets:
                        if (
                            isinstance(target, ast.Name)
                            and target.id == "ROBOTSTXT_OBEY"
                        ):
                            self.found_robotstxt_obey = True
                            if (
                                isinstance(child.value, ast.Constant)
                                and child.value.value is True
                            ):
                                self.robotstxt_obey_enabled = True
                            break

            if not self.found_robotstxt_obey or not self.robotstxt_obey_enabled:
                yield (
                    1,
                    0,
                    f"{self.msg_code}: ROBOTSTXT_OBEY not enabled in settings.py",
                )


class ThrottlingConfigIssueFinder:
    msg_code = "SCP21"

    def __init__(self, filename):
        self.filename = filename

    def find_issues(self, node):  # noqa: PLR0912
        if not (self.filename and self.filename.endswith("settings.py")):
            return

        if not isinstance(node, ast.Module):
            return

        autothrottle_enabled = False
        found_settings = set()
        required_settings = {
            "CONCURRENT_REQUESTS",
            "CONCURRENT_REQUESTS_PER_DOMAIN",
            "DOWNLOAD_DELAY",
        }

        for child in ast.walk(node):
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        if target.id == "AUTOTHROTTLE_ENABLED":
                            if (
                                isinstance(child.value, ast.Constant)
                                and child.value.value is True
                            ):
                                autothrottle_enabled = True
                        elif target.id in required_settings:
                            found_settings.add(target.id)
            elif (
                isinstance(child, ast.Subscript)
                and isinstance(child.value, ast.Name)
                and child.value.id == "settings"
                and isinstance(child.slice, ast.Constant)
                and isinstance(child.slice.value, str)
            ):
                setting_name = child.slice.value
                if setting_name == "AUTOTHROTTLE_ENABLED":
                    parent = getattr(child, "parent", None)
                    if (
                        isinstance(parent, ast.Assign)
                        and isinstance(parent.value, ast.Constant)
                        and parent.value.value is True
                    ):
                        autothrottle_enabled = True
                elif setting_name in required_settings:
                    found_settings.add(setting_name)

        if not autothrottle_enabled and found_settings != required_settings:
            missing_settings = required_settings - found_settings
            if missing_settings:
                missing_list = ", ".join(sorted(missing_settings))
                yield (
                    1,
                    0,
                    f"{self.msg_code}: Incomplete throttling config in settings.py: enable AUTOTHROTTLE_ENABLED or set the following settings: {missing_list}",
                )


DEFAULT_SETTINGS = {
    "ADDONS",
    "AJAXCRAWL_ENABLED",
    "ASYNCIO_EVENT_LOOP",
    "AUTOTHROTTLE_DEBUG",
    "AUTOTHROTTLE_ENABLED",
    "AUTOTHROTTLE_MAX_DELAY",
    "AUTOTHROTTLE_START_DELAY",
    "AUTOTHROTTLE_TARGET_CONCURRENCY",
    "BOT_NAME",
    "CLOSESPIDER_ERRORCOUNT",
    "CLOSESPIDER_ITEMCOUNT",
    "CLOSESPIDER_PAGECOUNT",
    "CLOSESPIDER_TIMEOUT",
    "COMMANDS_MODULE",
    "COMPRESSION_ENABLED",
    "CONCURRENT_ITEMS",
    "CONCURRENT_REQUESTS",
    "CONCURRENT_REQUESTS_PER_DOMAIN",
    "CONCURRENT_REQUESTS_PER_IP",
    "COOKIES_DEBUG",
    "COOKIES_ENABLED",
    "DEFAULT_DROPITEM_LOG_LEVEL",
    "DEFAULT_ITEM_CLASS",
    "DEFAULT_REQUEST_HEADERS",
    "DEPTH_LIMIT",
    "DEPTH_PRIORITY",
    "DEPTH_STATS_VERBOSE",
    "DNSCACHE_ENABLED",
    "DNSCACHE_SIZE",
    "DNS_RESOLVER",
    "DNS_TIMEOUT",
    "DOWNLOAD_DELAY",
    "DOWNLOADER",
    "DOWNLOADER_CLIENTCONTEXTFACTORY",
    "DOWNLOADER_CLIENT_TLS_CIPHERS",
    "DOWNLOADER_CLIENT_TLS_METHOD",
    "DOWNLOADER_CLIENT_TLS_VERBOSE_LOGGING",
    "DOWNLOADER_HTTPCLIENTFACTORY",
    "DOWNLOADER_MIDDLEWARES",
    "DOWNLOADER_MIDDLEWARES_BASE",
    "DOWNLOADER_STATS",
    "DOWNLOAD_FAIL_ON_DATALOSS",
    "DOWNLOAD_HANDLERS",
    "DOWNLOAD_HANDLERS_BASE",
    "DOWNLOAD_MAXSIZE",
    "DOWNLOAD_TIMEOUT",
    "DOWNLOAD_WARNSIZE",
    "DUPEFILTER_CLASS",
    "EDITOR",
    "EXTENSIONS",
    "EXTENSIONS_BASE",
    "FEED_EXPORT_BATCH_ITEM_COUNT",
    "FEED_EXPORT_ENCODING",
    "FEED_EXPORTERS",
    "FEED_EXPORTERS_BASE",
    "FEED_EXPORT_FIELDS",
    "FEED_EXPORT_INDENT",
    "FEEDS",
    "FEED_STORAGE_FTP_ACTIVE",
    "FEED_STORAGE_GCS_ACL",
    "FEED_STORAGES",
    "FEED_STORAGES_BASE",
    "FEED_STORE_EMPTY",
    "FEED_TEMPDIR",
    "FEED_URI_PARAMS",
    "FILES_STORE_GCS_ACL",
    "FORCE_CRAWLER_PROCESS",
    "FTP_PASSIVE_MODE",
    "FTP_PASSWORD",
    "FTP_USER",
    "GCS_PROJECT_ID",
    "HTTPCACHE_ALWAYS_STORE",
    "HTTPCACHE_DBM_MODULE",
    "HTTPCACHE_DIR",
    "HTTPCACHE_ENABLED",
    "HTTPCACHE_EXPIRATION_SECS",
    "HTTPCACHE_GZIP",
    "HTTPCACHE_IGNORE_HTTP_CODES",
    "HTTPCACHE_IGNORE_MISSING",
    "HTTPCACHE_IGNORE_RESPONSE_CACHE_CONTROLS",
    "HTTPCACHE_IGNORE_SCHEMES",
    "HTTPCACHE_POLICY",
    "HTTPCACHE_STORAGE",
    "HTTPPROXY_AUTH_ENCODING",
    "HTTPPROXY_ENABLED",
    "IMAGES_STORE_GCS_ACL",
    "ITEM_PIPELINES",
    "ITEM_PIPELINES_BASE",
    "ITEM_PROCESSOR",
    "JOBDIR",
    "LOG_DATEFORMAT",
    "LOG_ENABLED",
    "LOG_ENCODING",
    "LOG_FILE",
    "LOG_FILE_APPEND",
    "LOG_FORMAT",
    "LOG_FORMATTER",
    "LOG_LEVEL",
    "LOG_SHORT_NAMES",
    "LOGSTATS_INTERVAL",
    "LOG_STDOUT",
    "LOG_VERSIONS",
    "MAIL_FROM",
    "MAIL_HOST",
    "MAIL_PASS",
    "MAIL_PORT",
    "MAIL_USER",
    "MEMDEBUG_ENABLED",
    "MEMDEBUG_NOTIFY",
    "MEMUSAGE_CHECK_INTERVAL_SECONDS",
    "MEMUSAGE_ENABLED",
    "MEMUSAGE_LIMIT_MB",
    "MEMUSAGE_NOTIFY_MAIL",
    "MEMUSAGE_WARNING_MB",
    "METAREFRESH_ENABLED",
    "METAREFRESH_IGNORE_TAGS",
    "METAREFRESH_MAXDELAY",
    "NEWSPIDER_MODULE",
    "PERIODIC_LOG_DELTA",
    "PERIODIC_LOG_STATS",
    "PERIODIC_LOG_TIMING_ENABLED",
    "RANDOMIZE_DOWNLOAD_DELAY",
    "REACTOR_THREADPOOL_MAXSIZE",
    "REDIRECT_ENABLED",
    "REDIRECT_MAX_TIMES",
    "REDIRECT_PRIORITY_ADJUST",
    "REFERER_ENABLED",
    "REFERRER_POLICY",
    "REQUEST_FINGERPRINTER_CLASS",
    "REQUEST_FINGERPRINTER_IMPLEMENTATION",
    "RETRY_ENABLED",
    "RETRY_EXCEPTIONS",
    "RETRY_HTTP_CODES",
    "RETRY_PRIORITY_ADJUST",
    "RETRY_TIMES",
    "ROBOTSTXT_OBEY",
    "ROBOTSTXT_PARSER",
    "ROBOTSTXT_USER_AGENT",
    "SCHEDULER",
    "SCHEDULER_DEBUG",
    "SCHEDULER_DISK_QUEUE",
    "SCHEDULER_MEMORY_QUEUE",
    "SCHEDULER_PRIORITY_QUEUE",
    "SCHEDULER_START_DISK_QUEUE",
    "SCHEDULER_START_MEMORY_QUEUE",
    "SCRAPER_SLOT_MAX_ACTIVE_SIZE",
    "SPIDER_CONTRACTS",
    "SPIDER_CONTRACTS_BASE",
    "SPIDER_LOADER_CLASS",
    "SPIDER_LOADER_WARN_ONLY",
    "SPIDER_MIDDLEWARES",
    "SPIDER_MIDDLEWARES_BASE",
    "SPIDER_MODULES",
    "STATS_CLASS",
    "STATS_DUMP",
    "STATSMAILER_RCPTS",
    "TELNETCONSOLE_ENABLED",
    "TELNETCONSOLE_HOST",
    "TELNETCONSOLE_PASSWORD",
    "TELNETCONSOLE_PORT",
    "TELNETCONSOLE_USERNAME",
    "TEMPLATES_DIR",
    "TWISTED_REACTOR",
    "URLLENGTH_LIMIT",
    "USER_AGENT",
    "WARN_ON_GENERATOR_RETURN_VALUE",
}

DEFAULT_SETTINGS_WITH_NONE = {
    "FEED_EXPORT_ENCODING",
    "FEED_EXPORT_FIELDS",
    "FEED_TEMPDIR",
    "FEED_URI_PARAMS",
    "JOBDIR",
    "LOG_FILE",
    "MAIL_USER",
    "MAIL_PASS",
    "PERIODIC_LOG_DELTA",
    "PERIODIC_LOG_STATS",
    "ROBOTSTXT_USER_AGENT",
    "TELNETCONSOLE_PASSWORD",
}


class UnnecessaryGetIssueFinder(BaseSettingsIssueFinder):
    msg_code = "SCP25"
    msg_info = "unneeded get()"

    def __init__(self, filename=None, *args, **kwargs):
        super().__init__(filename, *args, **kwargs)

    def should_report_setting(self, setting_name: str) -> bool:
        # Only report if it's a known setting and doesn't have a specific typed getter (to avoid conflicts with SCP17)
        if setting_name not in SETTINGS:
            return False
        setting_info = SETTINGS[setting_name]
        if setting_info.type is not None:
            # Check if this type has a specific getter method defined in SCP17
            type_to_method = {
                SettingType.BOOL: "getbool",
                SettingType.INT: "getint",
                SettingType.FLOAT: "getfloat",
                SettingType.LIST: "getlist",
                SettingType.DICT: "getdict",
                SettingType.DICT_OR_LIST: "getdictorlist",
                SettingType.BASED_DICT: "getwithbase",
            }
            # Only report if the type doesn't have a specific getter (i.e., uses "get")
            return setting_info.type not in type_to_method
        return True

    def get_setting_message(self, setting_name: str) -> str:
        return f"{self.msg_code}: {self.msg_info}: use [] instead of get() to read {setting_name}"

    def check_assignment(
        self, node: ast.Assign
    ) -> Generator[tuple[int, int, str], None, None]:
        return
        yield  # pragma: no cover

    def check_call(self, node: ast.Call) -> Generator[tuple[int, int, str], None, None]:
        if not isinstance(node.func, ast.Attribute):
            return

        # Only check get() calls for SCP25, not typed getters (those are handled by SCP17)
        if self.is_settings_method_call(node) and node.func.attr == "get":
            yield from self.check_settings_method_args(node)

    def check_subscript(
        self, node: ast.Subscript
    ) -> Generator[tuple[int, int, str], None, None]:
        return
        yield  # pragma: no cover

    def check_delete(
        self, node: ast.Delete
    ) -> Generator[tuple[int, int, str], None, None]:
        return
        yield  # pragma: no cover

    def check_settings_method_args(
        self, node: ast.Call
    ) -> Generator[tuple[int, int, str], None, None]:
        assert isinstance(node.func, ast.Attribute)
        method_name = node.func.attr

        # Only handle get() calls for SCP25
        if method_name != "get":
            return

        first_arg = node.args[0] if node.args else None
        if (
            first_arg
            and isinstance(first_arg, ast.Constant)
            and isinstance(first_arg.value, str)
        ):
            MAX_ARGS_WITH_DEFAULT = 2
            first_arg = node.args[0] if node.args else None
            if (
                first_arg
                and isinstance(first_arg, ast.Constant)
                and isinstance(first_arg.value, str)
            ):
                setting_name = first_arg.value
                # Check if it's unneeded: no default or default is None
                if self.should_report_setting(setting_name) and (
                    len(node.args) == 1
                    or (
                        len(node.args) == MAX_ARGS_WITH_DEFAULT
                        and isinstance(node.args[1], ast.Constant)
                        and node.args[1].value is None
                    )
                ):
                    yield from self.report_setting_issue(
                        first_arg.lineno, first_arg.col_offset, setting_name
                    )

        # Check keyword arguments
        for keyword in node.keywords:
            if (
                keyword.arg == "name"
                and isinstance(keyword.value, ast.Constant)
                and isinstance(keyword.value.value, str)
            ):
                setting_name = keyword.value.value
                if self.should_report_setting(setting_name):
                    # Check if default is None or not provided
                    has_none_default = False
                    for kw in node.keywords:
                        if (
                            kw.arg == "default"
                            and isinstance(kw.value, ast.Constant)
                            and kw.value.value is None
                        ):
                            has_none_default = True
                            break

                    if (
                        not any(kw.arg == "default" for kw in node.keywords)
                        or has_none_default
                    ):
                        yield from self.report_setting_issue(
                            keyword.value.lineno, keyword.value.col_offset, setting_name
                        )


class IgnoredGetDefaultIssueFinder(BaseSettingsIssueFinder):
    msg_code = "SCP26"
    msg_info = "ignored getter default"

    def __init__(self, filename=None, *args, **kwargs):
        super().__init__(filename, *args, **kwargs)

    def should_report_setting(self, setting_name: str) -> bool:
        return setting_name in SETTINGS

    def get_setting_message(self, setting_name: str, method_name: str = "get") -> str:
        return (
            f"{self.msg_code}: {self.msg_info}: {setting_name} is set in "
            "scrapy.settings.default_settings with a non-None value, "
            f"so the default value passed to {method_name}() will never be used."
        )

    def check_assignment(
        self, node: ast.Assign
    ) -> Generator[tuple[int, int, str], None, None]:
        return
        yield  # pragma: no cover

    def check_call(self, node: ast.Call) -> Generator[tuple[int, int, str], None, None]:
        if not isinstance(node.func, ast.Attribute):
            return

        getter_methods = {
            "get",
            "getbool",
            "getint",
            "getfloat",
            "getlist",
            "getdict",
            "getdictorlist",
            "getwithbase",
        }

        if self.is_settings_method_call(node) and node.func.attr in getter_methods:
            yield from self.check_settings_method_args(node)

    def check_subscript(
        self, node: ast.Subscript
    ) -> Generator[tuple[int, int, str], None, None]:
        return
        yield  # pragma: no cover

    def check_delete(
        self, node: ast.Delete
    ) -> Generator[tuple[int, int, str], None, None]:
        return
        yield  # pragma: no cover

    def check_settings_method_args(
        self, node: ast.Call
    ) -> Generator[tuple[int, int, str], None, None]:
        assert isinstance(node.func, ast.Attribute)
        method_name = node.func.attr
        getter_methods = {
            "get",
            "getbool",
            "getint",
            "getfloat",
            "getlist",
            "getdict",
            "getdictorlist",
            "getwithbase",
        }

        if method_name not in getter_methods:
            return

        first_arg = node.args[0] if node.args else None
        if (
            first_arg
            and isinstance(first_arg, ast.Constant)
            and isinstance(first_arg.value, str)
        ):
            MAX_ARGS_WITH_DEFAULT = 2
            first_arg = node.args[0] if node.args else None
            if (
                first_arg
                and isinstance(first_arg, ast.Constant)
                and isinstance(first_arg.value, str)
            ):
                setting_name = first_arg.value
                if (
                    self.should_report_setting(setting_name)
                    and setting_name in DEFAULT_SETTINGS
                    and setting_name not in DEFAULT_SETTINGS_WITH_NONE
                    and len(node.args) == MAX_ARGS_WITH_DEFAULT
                    and not (
                        isinstance(node.args[1], ast.Constant)
                        and node.args[1].value is None
                    )
                ):
                    # Point to the default value (second argument) instead of setting name
                    default_arg = node.args[1]
                    if setting_name in self.found_settings:
                        return
                    self.found_settings.add(setting_name)
                    message = self.get_setting_message(setting_name, method_name)
                    yield (default_arg.lineno, default_arg.col_offset, message)

        # Check keyword arguments
        for keyword in node.keywords:
            if (
                keyword.arg == "name"
                and isinstance(keyword.value, ast.Constant)
                and isinstance(keyword.value.value, str)
            ):
                setting_name = keyword.value.value
                if (
                    self.should_report_setting(setting_name)
                    and setting_name in DEFAULT_SETTINGS
                    and setting_name not in DEFAULT_SETTINGS_WITH_NONE
                ):
                    # Check if there's a non-None default in keywords
                    for kw in node.keywords:
                        if kw.arg == "default" and not (
                            isinstance(kw.value, ast.Constant)
                            and kw.value.value is None
                        ):
                            if setting_name in self.found_settings:
                                return
                            self.found_settings.add(setting_name)
                            message = self.get_setting_message(
                                setting_name, method_name
                            )
                            yield (kw.value.lineno, kw.value.col_offset, message)
                            break


class DuplicateSettingsIssueFinder:
    msg_code = "SCP23"

    def __init__(self, filename):
        self.filename = filename

    def find_issues(self, node):
        if not (self.filename and self.filename.endswith("settings.py")):
            return

        if not isinstance(node, ast.Module):
            return

        seen_settings = {}

        for child in node.body:
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        setting_name = target.id
                        if setting_name in seen_settings:
                            yield (
                                child.lineno,
                                child.col_offset,
                                f"{self.msg_code}: {setting_name} is set multiple times in settings.py",
                            )
                        else:
                            seen_settings[setting_name] = child.lineno


class BaseSettingNameIssueFinder(BaseSettingsIssueFinder):
    msg_code = "SCP24"
    msg_info = "use of BASE setting"

    def __init__(self, filename=None, *args, **kwargs):
        super().__init__(filename, *args, **kwargs)

    def should_report_setting(self, setting_name: str) -> bool:
        return setting_name.endswith("_BASE") and setting_name in SETTINGS

    def get_setting_message(self, setting_name: str) -> str:
        return f"{self.msg_code}: {self.msg_info}: do not use {setting_name}, use {setting_name[:-5]} instead"
