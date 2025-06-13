from __future__ import annotations

from difflib import get_close_matches

from flake8_scrapy._finders.data import (
    HARDCODED_SUGGESTIONS,
    MAX_SUGGESTIONS,
    MIN_SUGGESTION_SCORE,
    SETTINGS,
)


class Config:
    def __init__(self, user_known_settings: set[str] | None = None):
        user_known_settings = user_known_settings or set()
        self.known_settings = set(SETTINGS) | user_known_settings

    def is_known_setting(self, name: str) -> bool:
        return name in self.known_settings

    def get_setting_suggestions(self, name: str) -> list[str]:
        normalized_name = name.upper()
        hardcoded = HARDCODED_SUGGESTIONS.get(normalized_name)
        if hardcoded:
            return hardcoded[:MAX_SUGGESTIONS]
        return get_close_matches(
            normalized_name,
            self.known_settings,
            n=MAX_SUGGESTIONS,
            cutoff=MIN_SUGGESTION_SCORE,
        )
