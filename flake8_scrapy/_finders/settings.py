from __future__ import annotations

import ast
from abc import ABC, abstractmethod
from dataclasses import dataclass
from difflib import get_close_matches
from pathlib import Path
from typing import TYPE_CHECKING

from packaging.utils import canonicalize_name
from packaging.version import Version

from . import MINIMUM_SUPPORTED_SCRAPY_VERSION, IssueFinder

if TYPE_CHECKING:
    from collections.abc import Generator

MIN_VALID_SETTING_NAME_LENGTH = 3


@dataclass
class SettingInfo:
    added_version: str | None = None
    removed_version: str | None = None
    deprecated_version: str | None = None
    deprecation_message: str | None = None


# Grouped by active, deprecated, removed, and plugin-specific.
# Active settings are sorted as in scrapy.settings.default_settings, while
# deprecated and removed settings are sorted by the version that deprecated or
# removed them, from higher to lower.
SETTINGS = {
    # Active settings
    "ADDONS": SettingInfo(added_version="2.10.0"),
    "ASYNCIO_EVENT_LOOP": SettingInfo(added_version="2.4.0"),
    "AUTOTHROTTLE_DEBUG": SettingInfo(),
    "AUTOTHROTTLE_ENABLED": SettingInfo(),
    "AUTOTHROTTLE_MAX_DELAY": SettingInfo(),
    "AUTOTHROTTLE_START_DELAY": SettingInfo(),
    "AUTOTHROTTLE_TARGET_CONCURRENCY": SettingInfo(),
    "BOT_NAME": SettingInfo(),
    "CLOSESPIDER_ERRORCOUNT": SettingInfo(),
    "CLOSESPIDER_ITEMCOUNT": SettingInfo(),
    "CLOSESPIDER_PAGECOUNT": SettingInfo(),
    "CLOSESPIDER_TIMEOUT": SettingInfo(),
    "COMMANDS_MODULE": SettingInfo(),
    "COMPRESSION_ENABLED": SettingInfo(),
    "CONCURRENT_ITEMS": SettingInfo(),
    "CONCURRENT_REQUESTS": SettingInfo(),
    "CONCURRENT_REQUESTS_PER_DOMAIN": SettingInfo(),
    "CONCURRENT_REQUESTS_PER_IP": SettingInfo(),
    "COOKIES_DEBUG": SettingInfo(),
    "COOKIES_ENABLED": SettingInfo(),
    "DEFAULT_DROPITEM_LOG_LEVEL": SettingInfo(added_version="2.13.0"),
    "DEFAULT_ITEM_CLASS": SettingInfo(),
    "DEFAULT_REQUEST_HEADERS": SettingInfo(),
    "DEPTH_LIMIT": SettingInfo(),
    "DEPTH_PRIORITY": SettingInfo(),
    "DEPTH_STATS_VERBOSE": SettingInfo(),
    "DNSCACHE_ENABLED": SettingInfo(),
    "DNSCACHE_SIZE": SettingInfo(),
    "DNS_RESOLVER": SettingInfo(),
    "DNS_TIMEOUT": SettingInfo(),
    "DOWNLOAD_DELAY": SettingInfo(),
    "DOWNLOAD_FAIL_ON_DATALOSS": SettingInfo(),
    "DOWNLOAD_HANDLERS": SettingInfo(),
    "DOWNLOAD_HANDLERS_BASE": SettingInfo(),
    "DOWNLOAD_MAXSIZE": SettingInfo(),
    "DOWNLOAD_TIMEOUT": SettingInfo(),
    "DOWNLOAD_WARNSIZE": SettingInfo(),
    "DOWNLOADER": SettingInfo(),
    "DOWNLOADER_CLIENTCONTEXTFACTORY": SettingInfo(),
    "DOWNLOADER_CLIENT_TLS_CIPHERS": SettingInfo(),
    "DOWNLOADER_CLIENT_TLS_METHOD": SettingInfo(),
    "DOWNLOADER_CLIENT_TLS_VERBOSE_LOGGING": SettingInfo(),
    "DOWNLOADER_HTTPCLIENTFACTORY": SettingInfo(),
    "DOWNLOADER_MIDDLEWARES": SettingInfo(),
    "DOWNLOADER_MIDDLEWARES_BASE": SettingInfo(),
    "DOWNLOADER_STATS": SettingInfo(),
    "DUPEFILTER_CLASS": SettingInfo(),
    "EDITOR": SettingInfo(),
    "EXTENSIONS": SettingInfo(),
    "EXTENSIONS_BASE": SettingInfo(),
    "FEED_EXPORT_BATCH_ITEM_COUNT": SettingInfo(added_version="2.3.0"),
    "FEED_EXPORT_ENCODING": SettingInfo(),
    "FEED_EXPORT_FIELDS": SettingInfo(),
    "FEED_EXPORT_INDENT": SettingInfo(),
    "FEED_EXPORTERS": SettingInfo(),
    "FEED_EXPORTERS_BASE": SettingInfo(),
    "FEED_STORAGE_FTP_ACTIVE": SettingInfo(),
    "FEED_STORAGE_GCS_ACL": SettingInfo(added_version="2.3.0"),
    "FEED_STORAGE_S3_ACL": SettingInfo(),
    "FEED_STORE_EMPTY": SettingInfo(),
    "FEED_STORAGES": SettingInfo(),
    "FEED_STORAGES_BASE": SettingInfo(),
    "FEED_TEMPDIR": SettingInfo(),
    "FEED_URI_PARAMS": SettingInfo(),
    "FEEDS": SettingInfo(added_version="2.1.0"),
    "FILES_STORE_GCS_ACL": SettingInfo(),
    "FILES_STORE_S3_ACL": SettingInfo(),
    "FORCE_CRAWLER_PROCESS": SettingInfo(),
    "FTP_PASSIVE_MODE": SettingInfo(),
    "FTP_PASSWORD": SettingInfo(),
    "FTP_USER": SettingInfo(),
    "GCS_PROJECT_ID": SettingInfo(added_version="2.3.0"),
    "HTTPCACHE_ALWAYS_STORE": SettingInfo(),
    "HTTPCACHE_DBM_MODULE": SettingInfo(),
    "HTTPCACHE_DIR": SettingInfo(),
    "HTTPCACHE_ENABLED": SettingInfo(),
    "HTTPCACHE_EXPIRATION_SECS": SettingInfo(),
    "HTTPCACHE_GZIP": SettingInfo(),
    "HTTPCACHE_IGNORE_HTTP_CODES": SettingInfo(),
    "HTTPCACHE_IGNORE_MISSING": SettingInfo(),
    "HTTPCACHE_IGNORE_RESPONSE_CACHE_CONTROLS": SettingInfo(),
    "HTTPCACHE_IGNORE_SCHEMES": SettingInfo(),
    "HTTPCACHE_POLICY": SettingInfo(),
    "HTTPCACHE_STORAGE": SettingInfo(),
    "HTTPPROXY_AUTH_ENCODING": SettingInfo(),
    "HTTPPROXY_ENABLED": SettingInfo(),
    "IMAGES_STORE_GCS_ACL": SettingInfo(),
    "IMAGES_STORE_S3_ACL": SettingInfo(),
    "ITEM_PIPELINES": SettingInfo(),
    "ITEM_PIPELINES_BASE": SettingInfo(),
    "ITEM_PROCESSOR": SettingInfo(),
    "JOBDIR": SettingInfo(),
    "LOG_DATEFORMAT": SettingInfo(),
    "LOG_ENABLED": SettingInfo(),
    "LOG_ENCODING": SettingInfo(),
    "LOG_FILE": SettingInfo(),
    "LOG_FILE_APPEND": SettingInfo(added_version="2.6.0"),
    "LOG_FORMAT": SettingInfo(),
    "LOG_FORMATTER": SettingInfo(),
    "LOG_LEVEL": SettingInfo(),
    "LOG_SHORT_NAMES": SettingInfo(),
    "LOG_STDOUT": SettingInfo(),
    "LOG_VERSIONS": SettingInfo(added_version="2.13.0"),
    "LOGSTATS_INTERVAL": SettingInfo(),
    "MAIL_FROM": SettingInfo(),
    "MAIL_HOST": SettingInfo(),
    "MAIL_PASS": SettingInfo(),
    "MAIL_PORT": SettingInfo(),
    "MAIL_USER": SettingInfo(),
    "MEMDEBUG_ENABLED": SettingInfo(),
    "MEMDEBUG_NOTIFY": SettingInfo(),
    "MEMUSAGE_CHECK_INTERVAL_SECONDS": SettingInfo(),
    "MEMUSAGE_ENABLED": SettingInfo(),
    "MEMUSAGE_LIMIT_MB": SettingInfo(),
    "MEMUSAGE_NOTIFY_MAIL": SettingInfo(),
    "MEMUSAGE_WARNING_MB": SettingInfo(),
    "METAREFRESH_ENABLED": SettingInfo(),
    "METAREFRESH_IGNORE_TAGS": SettingInfo(),
    "METAREFRESH_MAXDELAY": SettingInfo(),
    "NEWSPIDER_MODULE": SettingInfo(),
    "PERIODIC_LOG_DELTA": SettingInfo(added_version="2.11.0"),
    "PERIODIC_LOG_STATS": SettingInfo(added_version="2.11.0"),
    "PERIODIC_LOG_TIMING_ENABLED": SettingInfo(added_version="2.11.0"),
    "RANDOMIZE_DOWNLOAD_DELAY": SettingInfo(),
    "REACTOR_THREADPOOL_MAXSIZE": SettingInfo(),
    "REDIRECT_ENABLED": SettingInfo(),
    "REDIRECT_MAX_TIMES": SettingInfo(),
    "REDIRECT_PRIORITY_ADJUST": SettingInfo(),
    "REFERER_ENABLED": SettingInfo(),
    "REFERRER_POLICY": SettingInfo(),
    "REQUEST_FINGERPRINTER_CLASS": SettingInfo(added_version="2.7.0"),
    "RETRY_ENABLED": SettingInfo(),
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
    "SPIDER_CONTRACTS": SettingInfo(),
    "SPIDER_CONTRACTS_BASE": SettingInfo(),
    "SPIDER_LOADER_CLASS": SettingInfo(),
    "SPIDER_LOADER_WARN_ONLY": SettingInfo(),
    "SPIDER_MIDDLEWARES": SettingInfo(),
    "SPIDER_MIDDLEWARES_BASE": SettingInfo(),
    "SPIDER_MODULES": SettingInfo(),
    "STATS_CLASS": SettingInfo(),
    "STATS_DUMP": SettingInfo(),
    "STATSMAILER_RCPTS": SettingInfo(),
    "TELNETCONSOLE_ENABLED": SettingInfo(),
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
    "AZURE_CONNECTION_STRING": SettingInfo(),
    "AZURE_ACCOUNT_URL_WITH_SAS_TOKEN": SettingInfo(),
    "AZURE_ACCOUNT_URL": SettingInfo(),
    "AZURE_ACCOUNT_KEY": SettingInfo(),
    # scrapy-deltafetch plugin settings, in order of appearance in
    # https://github.com/scrapy-plugins/scrapy-deltafetch#usage
    "DELTAFETCH_ENABLED": SettingInfo(),
    "DELTAFETCH_DIR": SettingInfo(),
    "DELTAFETCH_RESET": SettingInfo(),
    # scrapy-feedexporter-dropbox plugin settings, in order of appearance in
    # https://github.com/scrapy-plugins/scrapy-feedexporter-dropbox
    "DROPBOX_API_TOKEN": SettingInfo(),
    # scrapy-frontera plugin settings, in order of appearance in
    # https://github.com/scrapinghub/scrapy-frontera#usage-and-features
    "FRONTERA_SCHEDULER_START_REQUESTS_TO_FRONTIER": SettingInfo(),
    "FRONTERA_SCHEDULER_REQUEST_CALLBACKS_TO_FRONTIER": SettingInfo(),
    "FRONTERA_SCHEDULER_STATE_ATTRIBUTES": SettingInfo(),
    "FRONTERA_SCHEDULER_CALLBACK_SLOT_PREFIX_MAP": SettingInfo(),
    "BACKEND": SettingInfo(),
    # scrapy-feedexporter-google-drive plugin settings, in order of appearance
    # in https://github.com/scrapy-plugins/scrapy-feedexporter-google-drive
    "GDRIVE_SERVICE_ACCOUNT_CREDENTIALS_JSON": SettingInfo(),
    # scrapy-feedexporter-google-sheets plugin settings, in order of appearance
    # in https://github.com/scrapy-plugins/scrapy-feedexporter-google-sheets
    "GOOGLE_CREDENTIALS": SettingInfo(),
    # hcf-backend plugin settings, in order of appearance in
    # https://github.com/scrapinghub/hcf-backend/blob/master/hcf_backend/backend.py
    "HCF_CONSUMER_MAX_REQUESTS": SettingInfo(),
    "HCF_CONSUMER_MAX_BATCHES": SettingInfo(),
    "MAX_NEXT_REQUESTS": SettingInfo(),
    "HCF_AUTH": SettingInfo(),
    "HCF_PROJECT_ID": SettingInfo(),
    "HCF_PRODUCER_FRONTIER": SettingInfo(),
    "HCF_PRODUCER_SLOT_PREFIX": SettingInfo(),
    "HCF_PRODUCER_NUMBER_OF_SLOTS": SettingInfo(),
    "HCF_PRODUCER_BATCH_SIZE": SettingInfo(),
    "HCF_CONSUMER_FRONTIER": SettingInfo(),
    "HCF_CONSUMER_SLOT": SettingInfo(),
    "HCF_CONSUMER_DONT_DELETE_REQUESTS": SettingInfo(),
    "HCF_CONSUMER_DELETE_BATCHES_ON_STOP": SettingInfo(),
    # scrapy-incremental plugin settings, in order of appearance in
    # https://github.com/scrapy-plugins/scrapy-incremental
    "SCRAPYCLOUD_API_KEY": SettingInfo(),
    "SCRAPYCLOUD_PROJECT_ID": SettingInfo(),
    "INCREMENTAL_PIPELINE_ITEM_UNIQUE_FIELD": SettingInfo(),
    "INCREMENTAL_PIPELINE_BATCH_SIZE": SettingInfo(),
    # scrapy-feedexporter-onedrive plugin settings, in order of appearance in
    # https://github.com/scrapy-plugins/scrapy-feedexporter-onedrive
    "ONEDRIVE_ACCESS_TOKEN": SettingInfo(),
    # scrapy-playwright plugin settings, in order of appearance in
    # https://github.com/scrapy-plugins/scrapy-playwright#supported-settings
    "PLAYWRIGHT_BROWSER_TYPE": SettingInfo(),
    "PLAYWRIGHT_LAUNCH_OPTIONS": SettingInfo(),
    "PLAYWRIGHT_CDP_URL": SettingInfo(),
    "PLAYWRIGHT_CONNECT_URL": SettingInfo(),
    "PLAYWRIGHT_CONNECT_KWARGS": SettingInfo(),
    "PLAYWRIGHT_CONTEXTS": SettingInfo(),
    "PLAYWRIGHT_MAX_CONTEXTS": SettingInfo(),
    "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": SettingInfo(),
    "PLAYWRIGHT_PROCESS_REQUEST_HEADERS": SettingInfo(),
    "PLAYWRIGHT_RESTART_DISCONNECTED_BROWSER": SettingInfo(),
    "PLAYWRIGHT_MAX_PAGES_PER_CONTEXT": SettingInfo(),
    "PLAYWRIGHT_ABORT_REQUEST": SettingInfo(),
    # scrapy-poet plugin settings, in order of appearance in
    # https://scrapy-poet.readthedocs.io/en/stable/settings.html
    "SCRAPY_POET_CACHE": SettingInfo(),
    "SCRAPY_POET_CACHE_ERRORS": SettingInfo(),
    "SCRAPY_POET_DISCOVER": SettingInfo(),
    "SCRAPY_POET_OVERRIDES": SettingInfo(),
    "SCRAPY_POET_PROVIDERS": SettingInfo(),
    "SCRAPY_POET_REQUEST_FINGERPRINTER_BASE_CLASS": SettingInfo(),
    "SCRAPY_POET_RULES": SettingInfo(),
    "SCRAPY_POET_TESTS_ADAPTER": SettingInfo(),
    "SCRAPY_POET_TESTS_DIR": SettingInfo(),
    # scrapy-redis plugin settings, in order of appearance in
    # https://github.com/rmax/scrapy-redis/wiki/Usage
    "SCHEDULER_SERIALIZER": SettingInfo(),
    "SCHEDULER_PERSIST": SettingInfo(),
    "SCHEDULER_QUEUE_CLASS": SettingInfo(),
    "SCHEDULER_IDLE_BEFORE_CLOSE": SettingInfo(),
    "REDIS_ITEMS_KEY": SettingInfo(),
    "REDIS_ITEMS_SERIALIZER": SettingInfo(),
    "REDIS_HOST": SettingInfo(),
    "REDIS_PORT": SettingInfo(),
    "REDIS_URL": SettingInfo(),
    "REDIS_PARAMS": SettingInfo(),
    "REDIS_START_URLS_AS_SET": SettingInfo(),
    "REDIS_START_URLS_KEY": SettingInfo(),
    "REDIS_ENCODING": SettingInfo(),
    # scrapyrt plugin settings, in order of appearance in
    # https://scrapyrt.readthedocs.io/en/latest/api.html#available-settings
    "SERVICE_ROOT": SettingInfo(),
    "CRAWL_MANAGER": SettingInfo(),
    "RESOURCES": SettingInfo(),
    "LOG_DIR": SettingInfo(),
    "TIMEOUT_LIMIT": SettingInfo(),
    "DEBUG": SettingInfo(),
    "PROJECT_SETTINGS": SettingInfo(),
    # scrapy-settings-log plugin settings, in order of appearance in
    # https://github.com/scrapy-plugins/scrapy-settings-log
    "SETTINGS_LOGGING_ENABLED": SettingInfo(),
    "SETTINGS_LOGGING_REGEX": SettingInfo(),
    "SETTINGS_LOGGING_INDENT": SettingInfo(),
    "MASKED_SENSITIVE_SETTINGS_ENABLED": SettingInfo(),
    # scrapy-feedexporter-sftp plugin settings, in order of appearance in
    # https://github.com/scrapy-plugins/scrapy-feedexporter-sftp
    "FEED_STORAGE_SFTP_PKEY": SettingInfo(),
    # spidermon plugin settings, in order of appearance in
    # https://spidermon.readthedocs.io/en/latest/settings.html
    "SPIDERMON_ENABLED": SettingInfo(),
    "SPIDERMON_EXPRESSIONS_MONITOR_CLASS": SettingInfo(),
    "SPIDERMON_PERIODIC_MONITORS": SettingInfo(),
    "SPIDERMON_SPIDER_CLOSE_MONITORS": SettingInfo(),
    "SPIDERMON_SPIDER_CLOSE_EXPRESSION_MONITORS": SettingInfo(),
    "SPIDERMON_SPIDER_OPEN_MONITORS": SettingInfo(),
    "SPIDERMON_SPIDER_OPEN_EXPRESSION_MONITORS": SettingInfo(),
    "SPIDERMON_ENGINE_STOP_MONITORS": SettingInfo(),
    "SPIDERMON_ENGINE_STOP_EXPRESSION_MONITORS": SettingInfo(),
    "SPIDERMON_ADD_FIELD_COVERAGE": SettingInfo(),
    "SPIDERMON_FIELD_COVERAGE_SKIP_NONE": SettingInfo(),
    "SPIDERMON_LIST_FIELDS_COVERAGE_LEVELS": SettingInfo(),
    "SPIDERMON_DICT_FIELDS_COVERAGE_LEVELS": SettingInfo(),
    "SPIDERMON_MONITOR_SKIPPING_RULES": SettingInfo(),
    # scrapy-zyte-api plugin settings, in order of appearance in
    # https://scrapy-zyte-api.readthedocs.io/en/latest/reference/settings.html
    "ZYTE_API_AUTO_FIELD_STATS": SettingInfo(),
    "ZYTE_API_AUTOMAP_PARAMS": SettingInfo(),
    "ZYTE_API_BROWSER_HEADERS": SettingInfo(),
    "ZYTE_API_COOKIE_MIDDLEWARE": SettingInfo(),
    "ZYTE_API_DEFAULT_PARAMS": SettingInfo(),
    "ZYTE_API_ENABLED": SettingInfo(),
    "ZYTE_API_EXPERIMENTAL_COOKIES_ENABLED": SettingInfo(),
    "ZYTE_API_FALLBACK_HTTP_HANDLER": SettingInfo(),
    "ZYTE_API_FALLBACK_HTTPS_HANDLER": SettingInfo(),
    "ZYTE_API_FALLBACK_REQUEST_FINGERPRINTER_CLASS": SettingInfo(),
    "ZYTE_API_KEY": SettingInfo(),
    "ZYTE_API_LOG_REQUESTS": SettingInfo(),
    "ZYTE_API_LOG_REQUESTS_TRUNCATE": SettingInfo(),
    "ZYTE_API_MAX_COOKIES": SettingInfo(),
    "ZYTE_API_MAX_REQUESTS": SettingInfo(),
    "ZYTE_API_PRESERVE_DELAY": SettingInfo(),
    "ZYTE_API_PROVIDER_PARAMS": SettingInfo(),
    "ZYTE_API_REFERRER_POLICY": SettingInfo(),
    "ZYTE_API_RETRY_POLICY": SettingInfo(),
    "ZYTE_API_SESSION_CHECKER": SettingInfo(),
    "ZYTE_API_SESSION_ENABLED": SettingInfo(),
    "ZYTE_API_SESSION_LOCATION": SettingInfo(),
    "ZYTE_API_SESSION_MAX_BAD_INITS": SettingInfo(),
    "ZYTE_API_SESSION_MAX_BAD_INITS_PER_POOL": SettingInfo(),
    "ZYTE_API_SESSION_MAX_CHECK_FAILURES": SettingInfo(),
    "ZYTE_API_SESSION_MAX_ERRORS": SettingInfo(),
    "ZYTE_API_SESSION_PARAMS": SettingInfo(),
    "ZYTE_API_SESSION_POOL_SIZE": SettingInfo(),
    "ZYTE_API_SESSION_POOL_SIZES": SettingInfo(),
    "ZYTE_API_SESSION_QUEUE_MAX_ATTEMPTS": SettingInfo(),
    "ZYTE_API_SESSION_QUEUE_WAIT_TIME": SettingInfo(),
    "ZYTE_API_SKIP_HEADERS": SettingInfo(),
    "ZYTE_API_TRANSPARENT_MODE": SettingInfo(),
    "ZYTE_API_USE_ENV_PROXY": SettingInfo(),
    # scrapy-zyte-smartproxy plugin settings, in order of appearance in
    # https://scrapy-zyte-smartproxy.readthedocs.io/en/latest/settings.html
    "ZYTE_SMARTPROXY_APIKEY": SettingInfo(),
    "ZYTE_SMARTPROXY_URL": SettingInfo(),
    "ZYTE_SMARTPROXY_MAXBANS": SettingInfo(),
    "ZYTE_SMARTPROXY_DOWNLOAD_TIMEOUT": SettingInfo(),
    "ZYTE_SMARTPROXY_PRESERVE_DELAY": SettingInfo(),
    "ZYTE_SMARTPROXY_DEFAULT_HEADERS": SettingInfo(),
    "ZYTE_SMARTPROXY_BACKOFF_STEP": SettingInfo(),
    "ZYTE_SMARTPROXY_BACKOFF_MAX": SettingInfo(),
    "ZYTE_SMARTPROXY_FORCE_ENABLE_ON_HTTP_CODES": SettingInfo(),
    "ZYTE_SMARTPROXY_KEEP_HEADERS": SettingInfo(),
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


class UnknownSettingsIssueFinder(BaseSettingsIssueFinder):
    msg_code = "SCP07"
    msg_info = "unknown Scrapy setting"

    def __init__(self, filename=None, allowed_settings=None, *args, **kwargs):
        super().__init__(*args, filename=filename, **kwargs)
        self.known_settings = set(SETTINGS)
        if allowed_settings:
            self.known_settings.update(allowed_settings)

    def should_report_setting(self, setting_name: str) -> bool:
        return setting_name not in self.known_settings

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


class DeprecatedSettingsIssueFinder(BaseSettingsIssueFinder):
    msg_code = "SCP08"
    msg_info = "deprecated Scrapy setting"

    def __init__(self, filename=None, allowed_settings=None, *args, **kwargs):
        super().__init__(filename, *args, **kwargs)
        self.deprecated_settings = self.get_deprecated_settings()
        self.allowed_settings = set(allowed_settings) if allowed_settings else set()

    def get_deprecated_settings(self) -> set[str]:
        deprecated = set()
        scrapy_version = self.get_package_version("scrapy")
        if scrapy_version is None:
            return deprecated
        for name, info in SETTINGS.items():
            if info.removed_version and Version(info.removed_version) <= scrapy_version:
                continue
            if info.added_version and Version(info.added_version) > scrapy_version:
                continue
            if (
                info.deprecated_version
                and Version(info.deprecated_version) <= scrapy_version
            ):
                deprecated.add(name)
        return deprecated

    def should_report_setting(self, setting_name: str) -> bool:
        return (
            setting_name in self.deprecated_settings
            and setting_name not in self.allowed_settings
        )

    def get_setting_message(self, setting_name: str) -> str:
        version = SETTINGS[setting_name].deprecated_version
        if version == MINIMUM_SUPPORTED_SCRAPY_VERSION:
            version = f"{MINIMUM_SUPPORTED_SCRAPY_VERSION} or earlier"
        message = f"{self.msg_code}: {self.msg_info}: {setting_name} (deprecated in Scrapy {version})"
        deprecation_message = SETTINGS[setting_name].deprecation_message
        if deprecation_message:
            message += f". {deprecation_message}"
        return message


class FutureSettingsIssueFinder(BaseSettingsIssueFinder):
    msg_code = "SCP09"
    msg_info = "future Scrapy setting"

    def __init__(self, filename=None, allowed_settings=None, *args, **kwargs):
        super().__init__(filename, *args, **kwargs)
        scrapy_version = self.get_package_version("scrapy")
        if scrapy_version is None:
            self.future_settings = set()
        else:
            self.future_settings = {
                name
                for name, info in SETTINGS.items()
                if info.added_version and Version(info.added_version) > scrapy_version
            }
        self.allowed_settings = set(allowed_settings) if allowed_settings else set()

    def should_report_setting(self, setting_name: str) -> bool:
        return (
            setting_name in self.future_settings
            and setting_name not in self.allowed_settings
        )

    def get_setting_message(self, setting_name: str) -> str:
        version = SETTINGS[setting_name].added_version
        return f"{self.msg_code}: {self.msg_info}: {setting_name} (added in Scrapy {version})"


class RemovedSettingsIssueFinder(BaseSettingsIssueFinder):
    msg_code = "SCP10"
    msg_info = "removed Scrapy setting"

    def __init__(self, filename=None, allowed_settings=None, *args, **kwargs):
        super().__init__(filename, *args, **kwargs)
        scrapy_version = self.get_package_version("scrapy")
        if scrapy_version is None:
            self.removed_settings = set()
        else:
            self.removed_settings = {
                name
                for name, info in SETTINGS.items()
                if info.removed_version
                and Version(info.removed_version) <= scrapy_version
            }
        self.allowed_settings = set(allowed_settings) if allowed_settings else set()

    def should_report_setting(self, setting_name: str) -> bool:
        return (
            setting_name in self.removed_settings
            and setting_name not in self.allowed_settings
        )

    def get_setting_message(self, setting_name: str) -> str:
        version = SETTINGS[setting_name].removed_version
        return f"{self.msg_code}: {self.msg_info}: {setting_name} (removed in Scrapy {version})"
