from __future__ import annotations

from packaging.version import Version

from flake8_scrapy.settings import Setting, SettingType, VersionedValue

from .packages import PACKAGES

PREDEFINED_SUGGESTIONS = {
    "CONCURRENCY": ["CONCURRENT_REQUESTS", "CONCURRENT_REQUESTS_PER_DOMAIN"],
    "DELAY": ["DOWNLOAD_DELAY"],
}
MAX_AUTOMATIC_SUGGESTIONS = 3
MIN_AUTOMATIC_SUGGESTION_SCORE = 0.6

FEEDS_KEY_VERSION_ADDED = {
    "batch_item_count": Version("2.3.0"),
    "item_classes": Version("2.6.0"),
    "item_filter": Version("2.6.0"),
    "item_export_kwargs": Version("2.4.0"),
    "overwrite": Version("2.4.0"),
    "postprocessing": Version("2.6.0"),
}

SETTINGS = {
    # Active (i.e. neither deprecated nor removed) Scrapy built-in settings, in
    # order of appearance in
    # https://github.com/scrapy/scrapy/blob/master/scrapy/settings/default_settings.py
    "ADDONS": Setting(added_in=Version("2.10.0"), type=SettingType.DICT),
    "AWS_ACCESS_KEY_ID": Setting(type=SettingType.OPT_STR),
    "AWS_SECRET_ACCESS_KEY": Setting(type=SettingType.OPT_STR),
    "AWS_SESSION_TOKEN": Setting(type=SettingType.OPT_STR),
    "AWS_ENDPOINT_URL": Setting(type=SettingType.OPT_STR),
    "AWS_USE_SSL": Setting(type=SettingType.BOOL),
    "AWS_VERIFY": Setting(type=SettingType.BOOL),
    "AWS_REGION_NAME": Setting(type=SettingType.OPT_STR),
    "ASYNCIO_EVENT_LOOP": Setting(added_in=Version("2.4.0"), type=SettingType.CLS),
    "AUTOTHROTTLE_DEBUG": Setting(type=SettingType.BOOL),
    "AUTOTHROTTLE_ENABLED": Setting(type=SettingType.BOOL),
    "AUTOTHROTTLE_MAX_DELAY": Setting(type=SettingType.FLOAT),
    "AUTOTHROTTLE_START_DELAY": Setting(type=SettingType.FLOAT),
    "AUTOTHROTTLE_TARGET_CONCURRENCY": Setting(type=SettingType.FLOAT),
    "BOT_NAME": Setting(type=SettingType.STR),
    "CLOSESPIDER_ERRORCOUNT": Setting(type=SettingType.INT),
    "CLOSESPIDER_ITEMCOUNT": Setting(type=SettingType.INT),
    "CLOSESPIDER_PAGECOUNT": Setting(type=SettingType.INT),
    "CLOSESPIDER_PAGECOUNT_NO_ITEM": Setting(
        type=SettingType.INT, added_in=Version("2.12.0")
    ),
    "CLOSESPIDER_TIMEOUT": Setting(type=SettingType.FLOAT),
    "CLOSESPIDER_TIMEOUT_NO_ITEM": Setting(
        type=SettingType.INT, added_in=Version("2.10.0")
    ),
    "COMMANDS_MODULE": Setting(type=SettingType.STR),
    "COMPRESSION_ENABLED": Setting(type=SettingType.BOOL),
    "CONCURRENT_ITEMS": Setting(type=SettingType.INT),
    "CONCURRENT_REQUESTS": Setting(type=SettingType.INT),
    "CONCURRENT_REQUESTS_PER_DOMAIN": Setting(type=SettingType.INT),
    "CONCURRENT_REQUESTS_PER_IP": Setting(type=SettingType.INT),
    "COOKIES_DEBUG": Setting(type=SettingType.BOOL),
    "COOKIES_ENABLED": Setting(type=SettingType.BOOL),
    "DEFAULT_DROPITEM_LOG_LEVEL": Setting(
        added_in=Version("2.13.0"), type=SettingType.LOG_LEVEL
    ),
    "DEFAULT_ITEM_CLASS": Setting(type=SettingType.CLS),
    "DEFAULT_REQUEST_HEADERS": Setting(type=SettingType.DICT),
    "DEPTH_LIMIT": Setting(type=SettingType.INT),
    "DEPTH_PRIORITY": Setting(type=SettingType.INT),
    "DEPTH_STATS_VERBOSE": Setting(type=SettingType.BOOL),
    "DNSCACHE_ENABLED": Setting(type=SettingType.BOOL),
    "DNSCACHE_SIZE": Setting(type=SettingType.INT),
    "DNS_RESOLVER": Setting(type=SettingType.CLS),
    "DNS_TIMEOUT": Setting(type=SettingType.FLOAT),
    "DOWNLOAD_DELAY": Setting(type=SettingType.FLOAT),
    "DOWNLOAD_FAIL_ON_DATALOSS": Setting(type=SettingType.BOOL),
    "DOWNLOAD_HANDLERS": Setting(type=SettingType.BASED_DICT),
    "DOWNLOAD_HANDLERS_BASE": Setting(),
    "DOWNLOAD_MAXSIZE": Setting(type=SettingType.INT),
    "DOWNLOAD_SLOTS": Setting(type=SettingType.DICT, added_in=Version("2.9.0")),
    "DOWNLOAD_TIMEOUT": Setting(type=SettingType.FLOAT),
    "DOWNLOAD_WARNSIZE": Setting(type=SettingType.INT),
    "DOWNLOADER": Setting(type=SettingType.CLS),
    "DOWNLOADER_CLIENT_TLS_CIPHERS": Setting(type=SettingType.STR),
    "DOWNLOADER_CLIENT_TLS_METHOD": Setting(
        type=SettingType.ENUM_STR,
        values=("TLS", "TLSv1.0", "TLSv1.1", "TLSv1.2"),
    ),
    "DOWNLOADER_CLIENT_TLS_VERBOSE_LOGGING": Setting(type=SettingType.BOOL),
    "DOWNLOADER_CLIENTCONTEXTFACTORY": Setting(type=SettingType.CLS),
    "DOWNLOADER_HTTPCLIENTFACTORY": Setting(type=SettingType.CLS),
    "DOWNLOADER_MIDDLEWARES": Setting(type=SettingType.BASED_DICT),
    "DOWNLOADER_MIDDLEWARES_BASE": Setting(),
    "DOWNLOADER_STATS": Setting(type=SettingType.BOOL),
    "DUPEFILTER_CLASS": Setting(type=SettingType.CLS),
    "DUPEFILTER_DEBUG": Setting(type=SettingType.BOOL),
    "EDITOR": Setting(type=SettingType.STR),
    "EXTENSIONS": Setting(type=SettingType.BASED_DICT),
    "EXTENSIONS_BASE": Setting(),
    "FEED_EXPORT_BATCH_ITEM_COUNT": Setting(
        added_in=Version("2.3.0"), type=SettingType.INT
    ),
    "FEED_EXPORT_ENCODING": Setting(type=SettingType.OPT_STR),
    "FEED_EXPORT_FIELDS": Setting(type=SettingType.DICT_OR_LIST),
    "FEED_EXPORT_INDENT": Setting(type=SettingType.OPT_INT),
    "FEED_EXPORTERS": Setting(type=SettingType.BASED_DICT),
    "FEED_EXPORTERS_BASE": Setting(),
    "FEED_STORAGE_FTP_ACTIVE": Setting(type=SettingType.BOOL),
    "FEED_STORAGE_GCS_ACL": Setting(
        added_in=Version("2.3.0"), type=SettingType.OPT_STR
    ),
    "FEED_STORAGE_S3_ACL": Setting(type=SettingType.OPT_STR),
    "FEED_STORE_EMPTY": Setting(type=SettingType.BOOL),
    "FEED_STORAGES": Setting(type=SettingType.BASED_DICT),
    "FEED_STORAGES_BASE": Setting(),
    "FEED_TEMPDIR": Setting(type=SettingType.OPT_PATH),
    "FEED_URI_PARAMS": Setting(type=SettingType.OPT_CALLABLE),
    "FEEDS": Setting(added_in=Version("2.1.0"), type=SettingType.DICT),
    "FILES_EXPIRES": Setting(type=SettingType.INT),
    "FILES_RESULT_FIELD": Setting(type=SettingType.OPT_STR),
    "FILES_STORE": Setting(type=SettingType.OPT_PATH),
    "FILES_STORE_GCS_ACL": Setting(type=SettingType.OPT_STR),
    "FILES_STORE_S3_ACL": Setting(type=SettingType.OPT_STR),
    "FILES_URLS_FIELD": Setting(type=SettingType.OPT_STR),
    "FORCE_CRAWLER_PROCESS": Setting(),
    "FTP_PASSIVE_MODE": Setting(type=SettingType.BOOL),
    "FTP_PASSWORD": Setting(type=SettingType.OPT_STR),
    "FTP_USER": Setting(type=SettingType.OPT_STR),
    "GCS_PROJECT_ID": Setting(added_in=Version("2.3.0"), type=SettingType.OPT_STR),
    "HTTPCACHE_ALWAYS_STORE": Setting(type=SettingType.BOOL),
    "HTTPCACHE_DBM_MODULE": Setting(type=SettingType.OPT_STR),
    "HTTPCACHE_DIR": Setting(type=SettingType.OPT_PATH),
    "HTTPCACHE_ENABLED": Setting(type=SettingType.BOOL),
    "HTTPCACHE_EXPIRATION_SECS": Setting(type=SettingType.INT),
    "HTTPCACHE_GZIP": Setting(type=SettingType.BOOL),
    "HTTPCACHE_IGNORE_HTTP_CODES": Setting(type=SettingType.LIST),
    "HTTPCACHE_IGNORE_MISSING": Setting(type=SettingType.BOOL),
    "HTTPCACHE_IGNORE_RESPONSE_CACHE_CONTROLS": Setting(type=SettingType.LIST),
    "HTTPCACHE_IGNORE_SCHEMES": Setting(type=SettingType.LIST),
    "HTTPCACHE_POLICY": Setting(type=SettingType.CLS),
    "HTTPCACHE_STORAGE": Setting(type=SettingType.CLS),
    "HTTPERROR_ALLOW_ALL": Setting(type=SettingType.BOOL),
    "HTTPERROR_ALLOWED_CODES": Setting(type=SettingType.LIST),
    "HTTPPROXY_AUTH_ENCODING": Setting(type=SettingType.OPT_STR),
    "HTTPPROXY_ENABLED": Setting(type=SettingType.BOOL),
    "IMAGES_EXPIRES": Setting(type=SettingType.INT),
    "IMAGES_MIN_HEIGHT": Setting(type=SettingType.INT),
    "IMAGES_MIN_WIDTH": Setting(type=SettingType.INT),
    "IMAGES_RESULT_FIELD": Setting(type=SettingType.OPT_STR),
    "IMAGES_STORE": Setting(type=SettingType.OPT_PATH),
    "IMAGES_STORE_GCS_ACL": Setting(type=SettingType.OPT_STR),
    "IMAGES_STORE_S3_ACL": Setting(type=SettingType.OPT_STR),
    "IMAGES_THUMBS": Setting(type=SettingType.DICT),
    "IMAGES_URLS_FIELD": Setting(type=SettingType.OPT_STR),
    "ITEM_PIPELINES": Setting(type=SettingType.BASED_DICT),
    "ITEM_PIPELINES_BASE": Setting(),
    "ITEM_PROCESSOR": Setting(type=SettingType.CLS),
    "JOBDIR": Setting(type=SettingType.OPT_PATH),
    "LOG_DATEFORMAT": Setting(type=SettingType.STR),
    "LOG_ENABLED": Setting(type=SettingType.BOOL),
    "LOG_ENCODING": Setting(type=SettingType.STR),
    "LOG_FILE": Setting(type=SettingType.OPT_PATH),
    "LOG_FILE_APPEND": Setting(added_in=Version("2.6.0"), type=SettingType.BOOL),
    "LOG_FORMAT": Setting(type=SettingType.STR),
    "LOG_FORMATTER": Setting(type=SettingType.CLS),
    "LOG_LEVEL": Setting(type=SettingType.LOG_LEVEL),
    "LOG_SHORT_NAMES": Setting(type=SettingType.BOOL),
    "LOG_STDOUT": Setting(type=SettingType.BOOL),
    "LOG_VERSIONS": Setting(added_in=Version("2.13.0"), type=SettingType.LIST),
    "LOGSTATS_INTERVAL": Setting(type=SettingType.FLOAT),
    "MAIL_FROM": Setting(type=SettingType.OPT_STR),
    "MAIL_HOST": Setting(type=SettingType.OPT_STR),
    "MAIL_PASS": Setting(type=SettingType.OPT_STR),
    "MAIL_PORT": Setting(type=SettingType.OPT_STR),
    "MAIL_USER": Setting(type=SettingType.OPT_STR),
    "MAIL_TLS": Setting(type=SettingType.BOOL),
    "MAIL_SSL": Setting(type=SettingType.BOOL),
    "MEDIA_ALLOW_REDIRECTS": Setting(type=SettingType.BOOL),
    "MEMDEBUG_ENABLED": Setting(type=SettingType.BOOL),
    "MEMDEBUG_NOTIFY": Setting(type=SettingType.LIST),
    "MEMUSAGE_CHECK_INTERVAL_SECONDS": Setting(type=SettingType.FLOAT),
    "MEMUSAGE_ENABLED": Setting(type=SettingType.BOOL),
    "MEMUSAGE_LIMIT_MB": Setting(type=SettingType.INT),
    "MEMUSAGE_NOTIFY_MAIL": Setting(type=SettingType.LIST),
    "MEMUSAGE_WARNING_MB": Setting(type=SettingType.INT),
    "METAREFRESH_ENABLED": Setting(type=SettingType.BOOL),
    "METAREFRESH_IGNORE_TAGS": Setting(type=SettingType.LIST),
    "METAREFRESH_MAXDELAY": Setting(type=SettingType.INT),
    "NEWSPIDER_MODULE": Setting(type=SettingType.STR),
    "PERIODIC_LOG_DELTA": Setting(
        added_in=Version("2.11.0"), type=SettingType.PERIODIC_LOG_CONFIG
    ),
    "PERIODIC_LOG_STATS": Setting(
        added_in=Version("2.11.0"), type=SettingType.PERIODIC_LOG_CONFIG
    ),
    "PERIODIC_LOG_TIMING_ENABLED": Setting(
        added_in=Version("2.11.0"), type=SettingType.BOOL
    ),
    "RANDOMIZE_DOWNLOAD_DELAY": Setting(type=SettingType.BOOL),
    "REACTOR_THREADPOOL_MAXSIZE": Setting(type=SettingType.INT),
    "REDIRECT_ENABLED": Setting(type=SettingType.BOOL),
    "REDIRECT_MAX_TIMES": Setting(type=SettingType.INT),
    "REDIRECT_PRIORITY_ADJUST": Setting(type=SettingType.INT),
    "REFERER_ENABLED": Setting(type=SettingType.BOOL),
    "REFERRER_POLICY": Setting(type=SettingType.CLS),
    "REQUEST_FINGERPRINTER_CLASS": Setting(
        added_in=Version("2.7.0"), type=SettingType.CLS
    ),
    "RETRY_ENABLED": Setting(type=SettingType.BOOL),
    "RETRY_EXCEPTIONS": Setting(added_in=Version("2.10.0"), type=SettingType.LIST),
    "RETRY_HTTP_CODES": Setting(type=SettingType.LIST),
    "RETRY_PRIORITY_ADJUST": Setting(type=SettingType.INT),
    "RETRY_TIMES": Setting(type=SettingType.INT),
    "ROBOTSTXT_OBEY": Setting(type=SettingType.BOOL),
    "ROBOTSTXT_PARSER": Setting(type=SettingType.CLS),
    "ROBOTSTXT_USER_AGENT": Setting(type=SettingType.OPT_STR),
    "SCHEDULER": Setting(type=SettingType.CLS),
    "SCHEDULER_DEBUG": Setting(type=SettingType.BOOL),
    "SCHEDULER_DISK_QUEUE": Setting(type=SettingType.CLS),
    "SCHEDULER_MEMORY_QUEUE": Setting(type=SettingType.CLS),
    "SCHEDULER_PRIORITY_QUEUE": Setting(type=SettingType.CLS),
    "SCHEDULER_START_DISK_QUEUE": Setting(
        added_in=Version("2.13.0"), type=SettingType.CLS
    ),
    "SCHEDULER_START_MEMORY_QUEUE": Setting(
        added_in=Version("2.13.0"), type=SettingType.CLS
    ),
    "SCRAPER_SLOT_MAX_ACTIVE_SIZE": Setting(type=SettingType.INT),
    "SPIDER_CONTRACTS": Setting(type=SettingType.BASED_DICT),
    "SPIDER_CONTRACTS_BASE": Setting(),
    "SPIDER_LOADER_CLASS": Setting(type=SettingType.CLS),
    "SPIDER_LOADER_WARN_ONLY": Setting(type=SettingType.BOOL),
    "SPIDER_MIDDLEWARES": Setting(type=SettingType.BASED_DICT),
    "SPIDER_MIDDLEWARES_BASE": Setting(),
    "SPIDER_MODULES": Setting(type=SettingType.LIST),
    "STATS_CLASS": Setting(type=SettingType.CLS),
    "STATS_DUMP": Setting(type=SettingType.BOOL),
    "STATSMAILER_RCPTS": Setting(type=SettingType.LIST),
    "TELNETCONSOLE_ENABLED": Setting(type=SettingType.BOOL),
    "TELNETCONSOLE_HOST": Setting(type=SettingType.STR),
    "TELNETCONSOLE_PASSWORD": Setting(type=SettingType.OPT_STR),
    "TELNETCONSOLE_PORT": Setting(type=SettingType.LIST),
    "TELNETCONSOLE_USERNAME": Setting(type=SettingType.STR),
    "TEMPLATES_DIR": Setting(type=SettingType.OPT_PATH),
    "TWISTED_REACTOR": Setting(type=SettingType.CLS),
    "URLLENGTH_LIMIT": Setting(type=SettingType.INT),
    "USER_AGENT": Setting(type=SettingType.OPT_STR),
    "WARN_ON_GENERATOR_RETURN_VALUE": Setting(
        added_in=Version("2.13.0"), type=SettingType.BOOL
    ),
    # Deprecated Scrapy built-in settings, in reverse deprecation order.
    "AJAXCRAWL_ENABLED": Setting(
        added_in=Version("0.22.0"),
        deprecated_in=Version("2.13.0"),
        sunset_guidance=(
            "The setting is False by default, and setting it to True will stop"
            " working in a future version of Scrapy."
        ),
        type=SettingType.BOOL,
    ),
    "REQUEST_FINGERPRINTER_IMPLEMENTATION": Setting(
        added_in=Version("2.7.0"),
        deprecated_in=Version("2.12.0"),
        sunset_guidance=(
            "See https://flake8-scrapy.readthedocs.io/en/latest/rules/scp08.html"
            "#request_fingerprinter_implementation"
        ),
    ),
    "FEED_FORMAT": Setting(
        default_value=VersionedValue("jsonlines"),
        deprecated_in=Version("2.1.0"),
        sunset_guidance="use FEEDS instead",
    ),
    "FEED_URI": Setting(
        deprecated_in=Version("2.1.0"),
        sunset_guidance="Use FEEDS instead",
    ),
    # Removed Scrapy built-in settings, in reverse removal order.
    "SPIDER_MANAGER_CLASS": Setting(
        removed_in=Version("2.5.0"), deprecated_in=Version("1.0.0")
    ),
    "LOG_UNSERIALIZABLE_REQUESTS": Setting(
        removed_in=Version("2.1.0"),
        deprecated_in=PACKAGES["scrapy"].lowest_supported_version,
        sunset_guidance="Use SCHEDULER_DEBUG instead.",
    ),
    "REDIRECT_MAX_METAREFRESH_DELAY": Setting(
        removed_in=Version("2.1.0"),
        deprecated_in=PACKAGES["scrapy"].lowest_supported_version,
        sunset_guidance="Use METAREFRESH_MAXDELAY instead.",
    ),
    # scrapy-feedexporter-azure-storage plugin settings, in order of appearance
    # in https://github.com/scrapy-plugins/scrapy-feedexporter-azure-storage
    "AZURE_CONNECTION_STRING": Setting(package="scrapy-feedexporter-azure-storage"),
    "AZURE_ACCOUNT_URL_WITH_SAS_TOKEN": Setting(
        package="scrapy-feedexporter-azure-storage"
    ),
    "AZURE_ACCOUNT_URL": Setting(package="scrapy-feedexporter-azure-storage"),
    "AZURE_ACCOUNT_KEY": Setting(package="scrapy-feedexporter-azure-storage"),
    # scrapy-deltafetch plugin settings, in order of appearance in
    # https://github.com/scrapy-plugins/scrapy-deltafetch#usage
    "DELTAFETCH_ENABLED": Setting(package="scrapy-deltafetch", type=SettingType.BOOL),
    "DELTAFETCH_DIR": Setting(package="scrapy-deltafetch"),
    "DELTAFETCH_RESET": Setting(package="scrapy-deltafetch"),
    # scrapy-feedexporter-dropbox plugin settings, in order of appearance in
    # https://github.com/scrapy-plugins/scrapy-feedexporter-dropbox
    "DROPBOX_API_TOKEN": Setting(package="scrapy-feedexporter-dropbox"),
    # scrapy-frontera plugin settings, in order of appearance in
    # https://github.com/scrapinghub/scrapy-frontera#usage-and-features
    "FRONTERA_SCHEDULER_START_REQUESTS_TO_FRONTIER": Setting(package="scrapy-frontera"),
    "FRONTERA_SCHEDULER_REQUEST_CALLBACKS_TO_FRONTIER": Setting(
        package="scrapy-frontera"
    ),
    "FRONTERA_SCHEDULER_STATE_ATTRIBUTES": Setting(package="scrapy-frontera"),
    "FRONTERA_SCHEDULER_CALLBACK_SLOT_PREFIX_MAP": Setting(package="scrapy-frontera"),
    "BACKEND": Setting(package="scrapy-frontera"),
    # scrapy-feedexporter-google-drive plugin settings, in order of appearance
    # in https://github.com/scrapy-plugins/scrapy-feedexporter-google-drive
    "GDRIVE_SERVICE_ACCOUNT_CREDENTIALS_JSON": Setting(
        package="scrapy-feedexporter-google-drive"
    ),
    # scrapy-feedexporter-google-sheets plugin settings, in order of appearance
    # in https://github.com/scrapy-plugins/scrapy-feedexporter-google-sheets
    "GOOGLE_CREDENTIALS": Setting(package="scrapy-feedexporter-google-sheets"),
    # hcf-backend plugin settings, in order of appearance in
    # https://github.com/scrapinghub/hcf-backend/blob/master/hcf_backend/backend.py
    "HCF_CONSUMER_MAX_REQUESTS": Setting(package="hcf-backend"),
    "HCF_CONSUMER_MAX_BATCHES": Setting(package="hcf-backend"),
    "MAX_NEXT_REQUESTS": Setting(package="hcf-backend"),
    "HCF_AUTH": Setting(package="hcf-backend"),
    "HCF_PROJECT_ID": Setting(package="hcf-backend"),
    "HCF_PRODUCER_FRONTIER": Setting(package="hcf-backend"),
    "HCF_PRODUCER_SLOT_PREFIX": Setting(package="hcf-backend"),
    "HCF_PRODUCER_NUMBER_OF_SLOTS": Setting(package="hcf-backend"),
    "HCF_PRODUCER_BATCH_SIZE": Setting(package="hcf-backend"),
    "HCF_CONSUMER_FRONTIER": Setting(package="hcf-backend"),
    "HCF_CONSUMER_SLOT": Setting(package="hcf-backend"),
    "HCF_CONSUMER_DONT_DELETE_REQUESTS": Setting(package="hcf-backend"),
    "HCF_CONSUMER_DELETE_BATCHES_ON_STOP": Setting(package="hcf-backend"),
    # scrapy-incremental plugin settings, in order of appearance in
    # https://github.com/scrapy-plugins/scrapy-incremental
    "SCRAPYCLOUD_API_KEY": Setting(package="scrapy-incremental"),
    "SCRAPYCLOUD_PROJECT_ID": Setting(package="scrapy-incremental"),
    "INCREMENTAL_PIPELINE_ITEM_UNIQUE_FIELD": Setting(package="scrapy-incremental"),
    "INCREMENTAL_PIPELINE_BATCH_SIZE": Setting(package="scrapy-incremental"),
    # scrapy-feedexporter-onedrive plugin settings, in order of appearance in
    # https://github.com/scrapy-plugins/scrapy-feedexporter-onedrive
    "ONEDRIVE_ACCESS_TOKEN": Setting(package="scrapy-feedexporter-onedrive"),
    # scrapy-playwright plugin settings, in order of appearance in
    # https://github.com/scrapy-plugins/scrapy-playwright#supported-settings
    "PLAYWRIGHT_BROWSER_TYPE": Setting(package="scrapy-playwright"),
    "PLAYWRIGHT_LAUNCH_OPTIONS": Setting(package="scrapy-playwright"),
    "PLAYWRIGHT_CDP_URL": Setting(package="scrapy-playwright"),
    "PLAYWRIGHT_CONNECT_URL": Setting(package="scrapy-playwright"),
    "PLAYWRIGHT_CONNECT_KWARGS": Setting(package="scrapy-playwright"),
    "PLAYWRIGHT_CONTEXTS": Setting(package="scrapy-playwright"),
    "PLAYWRIGHT_MAX_CONTEXTS": Setting(package="scrapy-playwright"),
    "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": Setting(package="scrapy-playwright"),
    "PLAYWRIGHT_PROCESS_REQUEST_HEADERS": Setting(package="scrapy-playwright"),
    "PLAYWRIGHT_RESTART_DISCONNECTED_BROWSER": Setting(package="scrapy-playwright"),
    "PLAYWRIGHT_MAX_PAGES_PER_CONTEXT": Setting(package="scrapy-playwright"),
    "PLAYWRIGHT_ABORT_REQUEST": Setting(package="scrapy-playwright"),
    # scrapy-poet plugin settings, in order of appearance in
    # https://scrapy-poet.readthedocs.io/en/stable/settings.html
    "SCRAPY_POET_CACHE": Setting(package="scrapy-poet"),
    "SCRAPY_POET_CACHE_ERRORS": Setting(package="scrapy-poet"),
    "SCRAPY_POET_DISCOVER": Setting(package="scrapy-poet"),
    "SCRAPY_POET_OVERRIDES": Setting(
        deprecated_in=Version("0.9.0"),
        sunset_guidance="Use SCRAPY_POET_DISCOVER and/or SCRAPY_POET_RULES instead",
        package="scrapy-poet",
    ),
    "SCRAPY_POET_PROVIDERS": Setting(package="scrapy-poet"),
    "SCRAPY_POET_REQUEST_FINGERPRINTER_BASE_CLASS": Setting(package="scrapy-poet"),
    "SCRAPY_POET_RULES": Setting(package="scrapy-poet"),
    "SCRAPY_POET_TESTS_ADAPTER": Setting(package="scrapy-poet"),
    "SCRAPY_POET_TESTS_DIR": Setting(package="scrapy-poet"),
    # scrapy-redis plugin settings, in order of appearance in
    # https://github.com/rmax/scrapy-redis/wiki/Usage
    "SCHEDULER_SERIALIZER": Setting(package="scrapy-redis"),
    "SCHEDULER_PERSIST": Setting(package="scrapy-redis"),
    "SCHEDULER_QUEUE_CLASS": Setting(package="scrapy-redis"),
    "SCHEDULER_IDLE_BEFORE_CLOSE": Setting(package="scrapy-redis"),
    "REDIS_ITEMS_KEY": Setting(package="scrapy-redis"),
    "REDIS_ITEMS_SERIALIZER": Setting(package="scrapy-redis"),
    "REDIS_HOST": Setting(package="scrapy-redis"),
    "REDIS_PORT": Setting(package="scrapy-redis"),
    "REDIS_URL": Setting(package="scrapy-redis"),
    "REDIS_PARAMS": Setting(package="scrapy-redis"),
    "REDIS_START_URLS_AS_SET": Setting(package="scrapy-redis"),
    "REDIS_START_URLS_KEY": Setting(package="scrapy-redis"),
    "REDIS_ENCODING": Setting(package="scrapy-redis"),
    # scrapyrt plugin settings, in order of appearance in
    # https://scrapyrt.readthedocs.io/en/latest/api.html#available-settings
    "SERVICE_ROOT": Setting(package="scrapyrt"),
    "CRAWL_MANAGER": Setting(package="scrapyrt"),
    "RESOURCES": Setting(package="scrapyrt"),
    "LOG_DIR": Setting(package="scrapyrt"),
    "TIMEOUT_LIMIT": Setting(package="scrapyrt"),
    "DEBUG": Setting(package="scrapyrt"),
    "PROJECT_SETTINGS": Setting(package="scrapyrt"),
    # scrapy-settings-log plugin settings, in order of appearance in
    # https://github.com/scrapy-plugins/scrapy-settings-log
    "SETTINGS_LOGGING_ENABLED": Setting(
        package="scrapy-settings-log", type=SettingType.BOOL
    ),
    "SETTINGS_LOGGING_REGEX": Setting(package="scrapy-settings-log"),
    "SETTINGS_LOGGING_INDENT": Setting(package="scrapy-settings-log"),
    "MASKED_SENSITIVE_SETTINGS_ENABLED": Setting(
        package="scrapy-settings-log", type=SettingType.BOOL
    ),
    # scrapy-feedexporter-sftp plugin settings, in order of appearance in
    # https://github.com/scrapy-plugins/scrapy-feedexporter-sftp
    "FEED_STORAGE_SFTP_PKEY": Setting(package="scrapy-feedexporter-sftp"),
    # spidermon plugin settings, in order of appearance in
    # https://spidermon.readthedocs.io/en/latest/settings.html
    "SPIDERMON_ENABLED": Setting(package="spidermon", type=SettingType.BOOL),
    "SPIDERMON_EXPRESSIONS_MONITOR_CLASS": Setting(package="spidermon"),
    "SPIDERMON_PERIODIC_MONITORS": Setting(package="spidermon"),
    "SPIDERMON_SPIDER_CLOSE_MONITORS": Setting(package="spidermon"),
    "SPIDERMON_SPIDER_CLOSE_EXPRESSION_MONITORS": Setting(package="spidermon"),
    "SPIDERMON_SPIDER_OPEN_MONITORS": Setting(package="spidermon"),
    "SPIDERMON_SPIDER_OPEN_EXPRESSION_MONITORS": Setting(package="spidermon"),
    "SPIDERMON_ENGINE_STOP_MONITORS": Setting(package="spidermon"),
    "SPIDERMON_ENGINE_STOP_EXPRESSION_MONITORS": Setting(package="spidermon"),
    "SPIDERMON_ADD_FIELD_COVERAGE": Setting(package="spidermon"),
    "SPIDERMON_FIELD_COVERAGE_SKIP_NONE": Setting(package="spidermon"),
    "SPIDERMON_LIST_FIELDS_COVERAGE_LEVELS": Setting(package="spidermon"),
    "SPIDERMON_DICT_FIELDS_COVERAGE_LEVELS": Setting(package="spidermon"),
    "SPIDERMON_MONITOR_SKIPPING_RULES": Setting(package="spidermon"),
    # scrapy-zyte-api plugin settings, in order of appearance in
    # https://scrapy-zyte-api.readthedocs.io/en/latest/reference/settings.html
    "ZYTE_API_AUTO_FIELD_STATS": Setting(package="scrapy-zyte-api"),
    "ZYTE_API_AUTOMAP_PARAMS": Setting(package="scrapy-zyte-api"),
    "ZYTE_API_BROWSER_HEADERS": Setting(package="scrapy-zyte-api"),
    "ZYTE_API_COOKIE_MIDDLEWARE": Setting(package="scrapy-zyte-api"),
    "ZYTE_API_DEFAULT_PARAMS": Setting(package="scrapy-zyte-api"),
    "ZYTE_API_ENABLED": Setting(package="scrapy-zyte-api", type=SettingType.BOOL),
    "ZYTE_API_EXPERIMENTAL_COOKIES_ENABLED": Setting(
        package="scrapy-zyte-api", type=SettingType.BOOL
    ),
    "ZYTE_API_FALLBACK_HTTP_HANDLER": Setting(package="scrapy-zyte-api"),
    "ZYTE_API_FALLBACK_HTTPS_HANDLER": Setting(package="scrapy-zyte-api"),
    "ZYTE_API_FALLBACK_REQUEST_FINGERPRINTER_CLASS": Setting(package="scrapy-zyte-api"),
    "ZYTE_API_KEY": Setting(package="scrapy-zyte-api"),
    "ZYTE_API_LOG_REQUESTS": Setting(package="scrapy-zyte-api"),
    "ZYTE_API_LOG_REQUESTS_TRUNCATE": Setting(package="scrapy-zyte-api"),
    "ZYTE_API_MAX_COOKIES": Setting(package="scrapy-zyte-api"),
    "ZYTE_API_MAX_REQUESTS": Setting(package="scrapy-zyte-api"),
    "ZYTE_API_PRESERVE_DELAY": Setting(package="scrapy-zyte-api"),
    "ZYTE_API_PROVIDER_PARAMS": Setting(package="scrapy-zyte-api"),
    "ZYTE_API_REFERRER_POLICY": Setting(package="scrapy-zyte-api"),
    "ZYTE_API_RETRY_POLICY": Setting(package="scrapy-zyte-api"),
    "ZYTE_API_SESSION_CHECKER": Setting(package="scrapy-zyte-api"),
    "ZYTE_API_SESSION_ENABLED": Setting(
        package="scrapy-zyte-api", type=SettingType.BOOL
    ),
    "ZYTE_API_SESSION_LOCATION": Setting(package="scrapy-zyte-api"),
    "ZYTE_API_SESSION_MAX_BAD_INITS": Setting(package="scrapy-zyte-api"),
    "ZYTE_API_SESSION_MAX_BAD_INITS_PER_POOL": Setting(package="scrapy-zyte-api"),
    "ZYTE_API_SESSION_MAX_CHECK_FAILURES": Setting(package="scrapy-zyte-api"),
    "ZYTE_API_SESSION_MAX_ERRORS": Setting(package="scrapy-zyte-api"),
    "ZYTE_API_SESSION_PARAMS": Setting(package="scrapy-zyte-api"),
    "ZYTE_API_SESSION_POOL_SIZE": Setting(package="scrapy-zyte-api"),
    "ZYTE_API_SESSION_POOL_SIZES": Setting(package="scrapy-zyte-api"),
    "ZYTE_API_SESSION_QUEUE_MAX_ATTEMPTS": Setting(package="scrapy-zyte-api"),
    "ZYTE_API_SESSION_QUEUE_WAIT_TIME": Setting(package="scrapy-zyte-api"),
    "ZYTE_API_SKIP_HEADERS": Setting(package="scrapy-zyte-api"),
    "ZYTE_API_TRANSPARENT_MODE": Setting(package="scrapy-zyte-api"),
    "ZYTE_API_USE_ENV_PROXY": Setting(package="scrapy-zyte-api"),
    # scrapy-zyte-smartproxy plugin settings, in order of appearance in
    # https://scrapy-zyte-smartproxy.readthedocs.io/en/latest/settings.html
    "ZYTE_SMARTPROXY_APIKEY": Setting(package="scrapy-zyte-smartproxy"),
    "ZYTE_SMARTPROXY_URL": Setting(package="scrapy-zyte-smartproxy"),
    "ZYTE_SMARTPROXY_MAXBANS": Setting(package="scrapy-zyte-smartproxy"),
    "ZYTE_SMARTPROXY_DOWNLOAD_TIMEOUT": Setting(package="scrapy-zyte-smartproxy"),
    "ZYTE_SMARTPROXY_PRESERVE_DELAY": Setting(package="scrapy-zyte-smartproxy"),
    "ZYTE_SMARTPROXY_DEFAULT_HEADERS": Setting(package="scrapy-zyte-smartproxy"),
    "ZYTE_SMARTPROXY_BACKOFF_STEP": Setting(package="scrapy-zyte-smartproxy"),
    "ZYTE_SMARTPROXY_BACKOFF_MAX": Setting(package="scrapy-zyte-smartproxy"),
    "ZYTE_SMARTPROXY_FORCE_ENABLE_ON_HTTP_CODES": Setting(
        package="scrapy-zyte-smartproxy"
    ),
    "ZYTE_SMARTPROXY_KEEP_HEADERS": Setting(package="scrapy-zyte-smartproxy"),
}
