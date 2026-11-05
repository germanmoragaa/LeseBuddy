import logging
import time

import deepl

from app.core.config import Settings
from app.services.translation.provider import (
    TranslationNotConfiguredError,
    TranslationProviderError,
    TranslationQuotaExceededError,
    TranslationTimeoutError,
    UsageSnapshot,
)

# Note: callers (see app/api/deps.py's get_translation_provider) only ever construct this
# class when settings.deepl_api_key is non-empty — an empty key gets NullTranslationProvider
# instead, so this class's constructor assumes a key is present.

logger = logging.getLogger(__name__)

# LeseBuddy only ever translates from German — no source-language setting exists; see
# docs/decisions/0004-translations-and-dictionary.md for why that's a deliberate scope limit,
# not an oversight.
SOURCE_LANGUAGE = "DE"


class DeepLTranslationProvider:
    """Wraps the official `deepl` SDK (`DeepLClient`, not the deprecated `Translator`).

    Never logs text content or the API key — only character counts and latency.
    """

    def __init__(self, settings: Settings) -> None:
        self._client = deepl.DeepLClient(settings.deepl_api_key)
        self._usage_check_interval = settings.translation_usage_check_interval_seconds
        self._cached_usage: UsageSnapshot | None = None
        self._cached_usage_at: float = 0.0

    def translate(self, text: str, *, context: str | None, target_lang: str) -> str:
        started = time.monotonic()
        try:
            result = self._client.translate_text(
                text,
                source_lang=SOURCE_LANGUAGE,
                target_lang=target_lang,
                context=context,
            )
        except deepl.AuthorizationException as exc:
            raise TranslationNotConfiguredError from exc
        except deepl.QuotaExceededException as exc:
            raise TranslationQuotaExceededError from exc
        except deepl.ConnectionException as exc:
            raise TranslationTimeoutError from exc
        except deepl.DeepLException as exc:
            raise TranslationProviderError from exc
        else:
            elapsed_ms = (time.monotonic() - started) * 1000
            logger.info(
                "deepl translate: chars=%d target=%s latency_ms=%.0f",
                len(text),
                target_lang,
                elapsed_ms,
            )
            return result.text

    def get_usage(self) -> UsageSnapshot:
        """Returns a cached usage snapshot, refreshed at most every
        `translation_usage_check_interval_seconds`. Fails open: if the check itself fails,
        a stale-but-present snapshot (or an "unknown, assume fine" one) is returned rather
        than blocking the caller's actual translation on a broken diagnostic call."""
        now = time.monotonic()
        if (
            self._cached_usage is not None
            and now - self._cached_usage_at < self._usage_check_interval
        ):
            return self._cached_usage

        try:
            usage = self._client.get_usage()
        except deepl.DeepLException:
            logger.warning("Failed to refresh DeepL usage; proceeding without a fresh check.")
            return self._cached_usage or UsageSnapshot(characters_used=0, character_limit=0)

        snapshot = UsageSnapshot(
            characters_used=usage.character.count if usage.character.valid else 0,
            character_limit=usage.character.limit if usage.character.valid else 0,
        )
        self._cached_usage = snapshot
        self._cached_usage_at = now
        return snapshot
