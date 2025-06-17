from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from packaging.version import Version


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
class VersionedValue:
    def __init__(self, value: Any = None, history: dict[Version, Any] | None = None):
        self.all_time_value = value
        self.value_history = history or {}

    def __getitem__(self, version: Version) -> Any:
        if not self.value_history:
            return self.all_time_value
        applicable_versions = [v for v in self.value_history if v <= version]
        if not applicable_versions:
            return self.all_time_value
        latest_applicable = max(applicable_versions)
        return self.value_history[latest_applicable]


@dataclass
class Setting:
    added_in: Version | None = None
    deprecated_in: Version | None = None
    removed_in: Version | None = None
    type: SettingType | None = None
    package: str = "scrapy"
    values: tuple[Any, ...] | None = None
    sunset_guidance: str | None = None
    default_value: VersionedValue | None = None

    def __post_init__(self):
        if self.type == SettingType.ENUM_STR and not self.values:
            raise ValueError("ENUM_STR type settings must have allowed_values")

    @staticmethod
    def get(value: Any) -> Any:
        return value

    @staticmethod
    def getbool(value: Any) -> bool:
        try:
            return bool(int(value))
        except (ValueError, TypeError):
            pass
        if value in ("True", "true"):
            return True
        if value in ("False", "false"):
            return False
        raise ValueError(f"Cannot convert {value!r} to bool")

    @staticmethod
    def getint(value: Any) -> int:
        return int(value)

    @staticmethod
    def getfloat(value: Any) -> float:
        return float(value)

    @staticmethod
    def getlist(value: Any) -> list:
        if not value:
            return []
        if isinstance(value, str):
            return value.split(",")
        return list(value)

    @staticmethod
    def getdict(value: Any) -> dict:
        if isinstance(value, str):
            return json.loads(value)
        return dict(value)

    @staticmethod
    def getdictorlist(value: Any) -> dict | list:
        if value is None:
            return {}
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value.split(",")
        if isinstance(value, tuple):
            return list(value)
        return deepcopy(value)
