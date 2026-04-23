from __future__ import annotations


class Localizer:
    def __init__(self, strings: dict[str, dict[str, str]], primary_language: str = "zh-CN") -> None:
        self.strings = strings
        self.primary_language = primary_language

    @property
    def secondary_language(self) -> str:
        return "en-US" if self.primary_language == "zh-CN" else "zh-CN"

    def set_language(self, language: str) -> None:
        self.primary_language = language

    def text(self, key: str, language: str | None = None) -> str:
        active_language = language or self.primary_language
        return self.strings.get(active_language, {}).get(key, key)

    def bilingual(self, key: str) -> tuple[str, str]:
        return self.text(key, self.primary_language), self.text(key, self.secondary_language)

