from dataclasses import dataclass
from typing import Protocol


class TranslationNotConfiguredError(Exception):
    """Raised when no provider API key is configured, or the configured key is rejected."""


class TranslationQuotaExceededError(Exception):
    """Raised when the provider's usage quota (e.g. DeepL's monthly character limit) is used up."""


class TranslationTimeoutError(Exception):
    """Raised when the provider didn't respond in time."""


class TranslationProviderError(Exception):
    """Raised for any other provider-side failure not covered by a more specific error above."""


@dataclass
class UsageSnapshot:
    characters_used: int
    character_limit: int

    @property
    def fraction_used(self) -> float:
        if self.character_limit <= 0:
            return 0.0
        return self.characters_used / self.character_limit


class TranslationProvider(Protocol):
    def translate(self, text: str, *, context: str | None, target_lang: str) -> str: ...

    def get_usage(self) -> UsageSnapshot: ...


class NullTranslationProvider:
    """Returned when `DEEPL_API_KEY` is empty — the app still starts; any translation
    attempt raises the same clear, typed error a real provider would raise for a bad key."""

    def translate(self, text: str, *, context: str | None, target_lang: str) -> str:
        raise TranslationNotConfiguredError

    def get_usage(self) -> UsageSnapshot:
        raise TranslationNotConfiguredError
