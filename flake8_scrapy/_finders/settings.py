from __future__ import annotations

import ast
import json
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
    "AUTOTHROTTLE_DEBUG": SettingInfo(),
    "AUTOTHROTTLE_ENABLED": SettingInfo(type=SettingType.BOOL),
    "AUTOTHROTTLE_MAX_DELAY": SettingInfo(),
    "AUTOTHROTTLE_START_DELAY": SettingInfo(),
    "AUTOTHROTTLE_TARGET_CONCURRENCY": SettingInfo(),
    "BOT_NAME": SettingInfo(type=SettingType.STR),
    "CLOSESPIDER_ERRORCOUNT": SettingInfo(),
    "CLOSESPIDER_ITEMCOUNT": SettingInfo(),
    "CLOSESPIDER_PAGECOUNT": SettingInfo(),
    "CLOSESPIDER_TIMEOUT": SettingInfo(),
    "COMMANDS_MODULE": SettingInfo(),
    "COMPRESSION_ENABLED": SettingInfo(type=SettingType.BOOL),
    "CONCURRENT_ITEMS": SettingInfo(type=SettingType.INT),
    "CONCURRENT_REQUESTS": SettingInfo(type=SettingType.INT),
    "CONCURRENT_REQUESTS_PER_DOMAIN": SettingInfo(type=SettingType.INT),
    "CONCURRENT_REQUESTS_PER_IP": SettingInfo(type=SettingType.INT),
    "COOKIES_DEBUG": SettingInfo(),
    "COOKIES_ENABLED": SettingInfo(type=SettingType.BOOL),
    "DEFAULT_DROPITEM_LOG_LEVEL": SettingInfo(added_version="2.13.0"),
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
    "DOWNLOADER_CLIENT_TLS_CIPHERS": SettingInfo(),
    "DOWNLOADER_CLIENT_TLS_METHOD": SettingInfo(),
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
    "FEED_EXPORT_BATCH_ITEM_COUNT": SettingInfo(added_version="2.3.0"),
    "FEED_EXPORT_ENCODING": SettingInfo(),
    "FEED_EXPORT_FIELDS": SettingInfo(type=SettingType.DICT_OR_LIST),
    "FEED_EXPORT_INDENT": SettingInfo(),
    "FEED_EXPORTERS": SettingInfo(),
    "FEED_EXPORTERS_BASE": SettingInfo(),
    "FEED_STORAGE_FTP_ACTIVE": SettingInfo(),
    "FEED_STORAGE_GCS_ACL": SettingInfo(
        added_version="2.3.0", type=SettingType.OPT_STR
    ),
    "FEED_STORAGE_S3_ACL": SettingInfo(),
    "FEED_STORE_EMPTY": SettingInfo(),
    "FEED_STORAGES": SettingInfo(),
    "FEED_STORAGES_BASE": SettingInfo(),
    "FEED_TEMPDIR": SettingInfo(type=SettingType.OPT_PATH),
    "FEED_URI_PARAMS": SettingInfo(),
    "FEEDS": SettingInfo(added_version="2.1.0"),
    "FILES_STORE_GCS_ACL": SettingInfo(),
    "FILES_STORE_S3_ACL": SettingInfo(),
    "FORCE_CRAWLER_PROCESS": SettingInfo(),
    "FTP_PASSIVE_MODE": SettingInfo(type=SettingType.BOOL),
    "FTP_PASSWORD": SettingInfo(type=SettingType.OPT_STR),
    "FTP_USER": SettingInfo(type=SettingType.OPT_STR),
    "GCS_PROJECT_ID": SettingInfo(added_version="2.3.0", type=SettingType.OPT_STR),
    "HTTPCACHE_ALWAYS_STORE": SettingInfo(),
    "HTTPCACHE_DBM_MODULE": SettingInfo(),
    "HTTPCACHE_DIR": SettingInfo(),
    "HTTPCACHE_ENABLED": SettingInfo(type=SettingType.BOOL),
    "HTTPCACHE_EXPIRATION_SECS": SettingInfo(),
    "HTTPCACHE_GZIP": SettingInfo(),
    "HTTPCACHE_IGNORE_HTTP_CODES": SettingInfo(),
    "HTTPCACHE_IGNORE_MISSING": SettingInfo(),
    "HTTPCACHE_IGNORE_RESPONSE_CACHE_CONTROLS": SettingInfo(),
    "HTTPCACHE_IGNORE_SCHEMES": SettingInfo(),
    "HTTPCACHE_POLICY": SettingInfo(),
    "HTTPCACHE_STORAGE": SettingInfo(),
    "HTTPPROXY_AUTH_ENCODING": SettingInfo(),
    "HTTPPROXY_ENABLED": SettingInfo(type=SettingType.BOOL),
    "IMAGES_STORE_GCS_ACL": SettingInfo(),
    "IMAGES_STORE_S3_ACL": SettingInfo(),
    "ITEM_PIPELINES": SettingInfo(type=SettingType.BASED_DICT),
    "ITEM_PIPELINES_BASE": SettingInfo(),
    "ITEM_PROCESSOR": SettingInfo(),
    "JOBDIR": SettingInfo(type=SettingType.OPT_PATH),
    "LOG_DATEFORMAT": SettingInfo(type=SettingType.STR),
    "LOG_ENABLED": SettingInfo(type=SettingType.BOOL),
    "LOG_ENCODING": SettingInfo(type=SettingType.STR),
    "LOG_FILE": SettingInfo(type=SettingType.OPT_PATH),
    "LOG_FILE_APPEND": SettingInfo(added_version="2.6.0", type=SettingType.BOOL),
    "LOG_FORMAT": SettingInfo(type=SettingType.STR),
    "LOG_FORMATTER": SettingInfo(type=SettingType.CLS),
    "LOG_LEVEL": SettingInfo(),
    "LOG_SHORT_NAMES": SettingInfo(type=SettingType.BOOL),
    "LOG_STDOUT": SettingInfo(type=SettingType.BOOL),
    "LOG_VERSIONS": SettingInfo(added_version="2.13.0", type=SettingType.LIST),
    "LOGSTATS_INTERVAL": SettingInfo(type=SettingType.FLOAT),
    "MAIL_FROM": SettingInfo(),
    "MAIL_HOST": SettingInfo(),
    "MAIL_PASS": SettingInfo(),
    "MAIL_PORT": SettingInfo(),
    "MAIL_USER": SettingInfo(),
    "MEMDEBUG_ENABLED": SettingInfo(type=SettingType.BOOL),
    "MEMDEBUG_NOTIFY": SettingInfo(type=SettingType.LIST),
    "MEMUSAGE_CHECK_INTERVAL_SECONDS": SettingInfo(type=SettingType.FLOAT),
    "MEMUSAGE_ENABLED": SettingInfo(type=SettingType.BOOL),
    "MEMUSAGE_LIMIT_MB": SettingInfo(type=SettingType.INT),
    "MEMUSAGE_NOTIFY_MAIL": SettingInfo(type=SettingType.LIST),
    "MEMUSAGE_WARNING_MB": SettingInfo(type=SettingType.INT),
    "METAREFRESH_ENABLED": SettingInfo(type=SettingType.BOOL),
    "METAREFRESH_IGNORE_TAGS": SettingInfo(),
    "METAREFRESH_MAXDELAY": SettingInfo(),
    "NEWSPIDER_MODULE": SettingInfo(),
    "PERIODIC_LOG_DELTA": SettingInfo(added_version="2.11.0"),
    "PERIODIC_LOG_STATS": SettingInfo(added_version="2.11.0"),
    "PERIODIC_LOG_TIMING_ENABLED": SettingInfo(
        added_version="2.11.0", type=SettingType.BOOL
    ),
    "RANDOMIZE_DOWNLOAD_DELAY": SettingInfo(type=SettingType.BOOL),
    "REACTOR_THREADPOOL_MAXSIZE": SettingInfo(),
    "REDIRECT_ENABLED": SettingInfo(type=SettingType.BOOL),
    "REDIRECT_MAX_TIMES": SettingInfo(),
    "REDIRECT_PRIORITY_ADJUST": SettingInfo(),
    "REFERER_ENABLED": SettingInfo(type=SettingType.BOOL),
    "REFERRER_POLICY": SettingInfo(),
    "REQUEST_FINGERPRINTER_CLASS": SettingInfo(added_version="2.7.0"),
    "RETRY_ENABLED": SettingInfo(type=SettingType.BOOL),
    "RETRY_EXCEPTIONS": SettingInfo(added_version="2.10.0"),
    "RETRY_HTTP_CODES": SettingInfo(),
    "RETRY_PRIORITY_ADJUST": SettingInfo(),
    "RETRY_TIMES": SettingInfo(),
    "ROBOTSTXT_OBEY": SettingInfo(),
    "ROBOTSTXT_PARSER": SettingInfo(),
    "ROBOTSTXT_USER_AGENT": SettingInfo(),
    "SCHEDULER": SettingInfo(),
    "SCHEDULER_DEBUG": SettingInfo(),
    "SCHEDULER_DISK_QUEUE": SettingInfo(),
    "SCHEDULER_MEMORY_QUEUE": SettingInfo(),
    "SCHEDULER_PRIORITY_QUEUE": SettingInfo(),
    "SCHEDULER_START_DISK_QUEUE": SettingInfo(added_version="2.13.0"),
    "SCHEDULER_START_MEMORY_QUEUE": SettingInfo(added_version="2.13.0"),
    "SCRAPER_SLOT_MAX_ACTIVE_SIZE": SettingInfo(),
    "SPIDER_CONTRACTS": SettingInfo(type=SettingType.BASED_DICT),
    "SPIDER_CONTRACTS_BASE": SettingInfo(),
    "SPIDER_LOADER_CLASS": SettingInfo(),
    "SPIDER_LOADER_WARN_ONLY": SettingInfo(),
    "SPIDER_MIDDLEWARES": SettingInfo(),
    "SPIDER_MIDDLEWARES_BASE": SettingInfo(),
    "SPIDER_MODULES": SettingInfo(),
    "STATS_CLASS": SettingInfo(),
    "STATS_DUMP": SettingInfo(),
    "STATSMAILER_RCPTS": SettingInfo(),
    "TELNETCONSOLE_ENABLED": SettingInfo(type=SettingType.BOOL),
    "TELNETCONSOLE_HOST": SettingInfo(),
    "TELNETCONSOLE_PASSWORD": SettingInfo(),
    "TELNETCONSOLE_PORT": SettingInfo(),
    "TELNETCONSOLE_USERNAME": SettingInfo(),
    "TEMPLATES_DIR": SettingInfo(),
    "TWISTED_REACTOR": SettingInfo(),
    "URLLENGTH_LIMIT": SettingInfo(),
    "USER_AGENT": SettingInfo(),
    "WARN_ON_GENERATOR_RETURN_VALUE": SettingInfo(added_version="2.13.0"),
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
            if info.type in (
                SettingType.BOOL,
                SettingType.INT,
                SettingType.FLOAT,
                SettingType.LIST,
                SettingType.DICT,
                SettingType.DICT_OR_LIST,
                SettingType.BASED_DICT,
            ):
                self.typed_settings[name] = info.type
        self._init_allowed_exclude_settings(allowed_settings, exclude_settings)
        self.validators = {
            SettingType.BOOL: lambda v: v in self.VALID_BOOL_LITERALS,
            SettingType.INT: self._can_convert_to_int,
            SettingType.FLOAT: self._can_convert_to_float,
            SettingType.LIST: self._can_convert_to_list,
            SettingType.DICT: self._can_convert_to_dict,
            SettingType.BASED_DICT: self._can_convert_to_dict,
            SettingType.DICT_OR_LIST: self._is_valid_dict_or_list_value,
        }

    def should_report_setting(self, setting_name: str) -> bool:
        return (
            setting_name in self.typed_settings
            and setting_name not in self.allowed_settings
            and setting_name not in self.exclude_settings
        )

    def get_setting_message(self, setting_name: str) -> str:
        setting_type = self.typed_settings[setting_name]

        type_messages = {
            SettingType.BOOL: f"only supports the following values: {', '.join(map(repr, self.VALID_BOOL_LITERALS))}.",
            SettingType.INT: "only supports values that can be passed to int()",
            SettingType.FLOAT: "only supports values that can be passed to float()",
            SettingType.LIST: "only supports values that can be passed to list()",
            SettingType.DICT: "only supports values that can be passed to dict() or strings defining a JSON object",
            SettingType.BASED_DICT: "only supports values that can be passed to dict() or strings defining a JSON object",
            SettingType.DICT_OR_LIST: "only supports None, str, tuple, dict, or list values",
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

    def _is_invalid_value(self, value_node: ast.AST, setting_name: str) -> bool:
        """Check if a value node represents an invalid value for the given setting."""
        setting_type = self.typed_settings[setting_name]

        # If we can identify the literal value
        if isinstance(value_node, ast.Constant):
            return self._is_invalid_constant_value(value_node.value, setting_type)

        # If we can identify the type but not the literal value
        if hasattr(value_node, "__class__"):
            return self._is_invalid_ast_node_type(value_node, setting_type)

        return False

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
        expected_method = self.TYPE_TO_METHOD[setting_type]
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
                if self.should_report_setting(setting_name):
                    setting_type = self.typed_settings[setting_name]
                    expected_method = self.TYPE_TO_METHOD[setting_type]
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
            if self.should_report_setting(setting_name):
                setting_type = self.typed_settings[setting_name]
                expected_method = self.TYPE_TO_METHOD[setting_type]
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
