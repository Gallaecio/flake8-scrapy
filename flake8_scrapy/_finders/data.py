from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

LATEST_KNOWN_SCRAPY_VERSION = "2.13.1"
MIN_SUGGESTION_SCORE = 0.6
MINIMUM_SUPPORTED_SCRAPY_VERSION = "2.0.1"

HARDCODED_SUGGESTIONS = {
    "CONCURRENCY": ["CONCURRENT_REQUESTS", "CONCURRENT_REQUESTS_PER_DOMAIN"],
    "DELAY": ["DOWNLOAD_DELAY"],
}


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


@dataclass
class SettingInfo:
    added_version: str | None = None
    deprecated_version: str | None = None
    removed_version: str | None = None
    type: SettingType | None = None
    package: str = "scrapy"
    allowed_values: tuple[str, ...] | None = None
    deprecation_message: str | None = None

    def __post_init__(self):
        if self.type == SettingType.ENUM_STR and not self.allowed_values:
            raise ValueError("ENUM_STR type settings must have allowed_values")


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
