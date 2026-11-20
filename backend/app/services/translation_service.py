import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models import Article, TranslationCache, TranslationRequestLog, User
from app.services.analysis_service import get_or_create_analysis
from app.services.selection import ResolvedSelection, resolve_selection
from app.services.translation.provider import (
    TranslationNotConfiguredError,
    TranslationProvider,
    TranslationProviderError,
    TranslationQuotaExceededError,
    TranslationTimeoutError,
)

PROVIDER_NAME = "deepl"


class TranslationRateLimitedError(Exception):
    """Raised when a user has made too many non-cached translation requests in the last hour."""

    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after


# Everything a translation attempt can raise that means "no translation right now, try again
# later" - vocabulary save catches exactly these so DeepL can never block saving a word.
RETRYABLE_TRANSLATION_ERRORS = (
    TranslationNotConfiguredError,
    TranslationQuotaExceededError,
    TranslationTimeoutError,
    TranslationProviderError,
    TranslationRateLimitedError,
)


def _cache_key(source_text: str, context: str | None, target_lang: str, provider: str) -> str:
    raw = f"{source_text}\0{context or ''}\0{target_lang}\0{provider}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _get_cached(db: Session, key: str) -> TranslationCache | None:
    return db.scalar(select(TranslationCache).where(TranslationCache.cache_key == key))


def lookup_cached_translation(
    db: Session, source_text: str, context: str | None, target_lang: str
) -> str | None:
    """Cache-only lookup — never calls the provider, never rate-limited, never logged."""
    key = _cache_key(source_text, context, target_lang, PROVIDER_NAME)
    cached = _get_cached(db, key)
    return cached.translated_text if cached is not None else None


def _check_rate_limit(db: Session, user: User, settings: Settings) -> None:
    now = datetime.now(UTC)
    hour_ago = now - timedelta(hours=1)
    rows_in_last_hour = db.scalars(
        select(TranslationRequestLog)
        .where(
            TranslationRequestLog.user_id == user.id,
            TranslationRequestLog.created_at > hour_ago,
        )
        .order_by(TranslationRequestLog.created_at.asc())
    ).all()
    if len(rows_in_last_hour) >= settings.translation_rate_limit_per_hour:
        oldest = rows_in_last_hour[0]
        elapsed = (now - oldest.created_at).total_seconds()
        raise TranslationRateLimitedError(retry_after=int(3600 - elapsed) + 1)


def _translate_cached(
    db: Session,
    provider: TranslationProvider,
    user: User,
    settings: Settings,
    *,
    source_text: str,
    context: str | None,
    target_lang: str,
) -> str:
    """Looks up the cache first (keyed by user-independent inputs only); on a miss, enforces
    the per-user rate limit and the proactive quota check, calls the real provider, caches the
    result, and logs the request — in that order, so a cache hit never touches the rate limit
    or the provider at all."""
    key = _cache_key(source_text, context, target_lang, PROVIDER_NAME)
    cached = _get_cached(db, key)
    if cached is not None:
        return cached.translated_text

    _check_rate_limit(db, user, settings)

    usage = provider.get_usage()
    if usage.character_limit > 0 and usage.fraction_used >= 1.0:
        raise TranslationQuotaExceededError

    translated_text = provider.translate(source_text, context=context, target_lang=target_lang)

    row = TranslationCache(
        cache_key=key,
        source_text=source_text,
        context=context,
        target_lang=target_lang,
        provider=PROVIDER_NAME,
        translated_text=translated_text,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        # A concurrent request cached the same (source_text, context, target_lang) first —
        # use its result rather than erroring, mirroring get_or_create_analysis's race handling.
        db.rollback()
        existing = _get_cached(db, key)
        assert existing is not None
        translated_text = existing.translated_text
    else:
        db.refresh(row)

    db.add(TranslationRequestLog(user_id=user.id))
    db.commit()

    return translated_text


def translate_text(
    db: Session,
    provider: TranslationProvider,
    user: User,
    *,
    source_text: str,
    context: str | None,
) -> str:
    """Cached, rate-limited translation into the user's language - the public entry point
    for callers other than the /translate endpoint (vocabulary save, retry, backfill)."""
    return _translate_cached(
        db,
        provider,
        user,
        get_settings(),
        source_text=source_text,
        context=context,
        target_lang=user.translation_language,
    )


def context_translation_request(
    selection: ResolvedSelection, original_text: str
) -> tuple[str, str | None]:
    """(source_text, deepl_context) for translating a selection's context unit: a song line
    goes with its neighbouring lines as DeepL context, a text sentence on its own (as it
    always has, so the existing cache entries stay valid)."""
    return selection.context_text(original_text), selection.surrounding_context


@dataclass
class TranslateResult:
    selection_translation: str
    sentence_translation: str | None
    quota_warning: str | None


def translate_selection(
    db: Session,
    provider: TranslationProvider,
    user: User,
    article: Article,
    start: int,
    end: int,
    include_sentence: bool,
) -> TranslateResult:
    settings = get_settings()
    analysis = get_or_create_analysis(db, article)
    selection = resolve_selection(analysis, article.original_text, start, end, kind=article.kind)
    context = selection.context_text(article.original_text)
    target_lang = user.translation_language

    selection_translation = _translate_cached(
        db,
        provider,
        user,
        settings,
        source_text=selection.surface_text,
        context=context,
        target_lang=target_lang,
    )

    # For songs this is the lyric line's translation (its neighbours as DeepL context); the
    # response field keeps its historical name.
    sentence_translation = None
    if include_sentence:
        line_text, line_context = context_translation_request(selection, article.original_text)
        sentence_translation = _translate_cached(
            db,
            provider,
            user,
            settings,
            source_text=line_text,
            context=line_context,
            target_lang=target_lang,
        )

    # Best-effort only: a fully-cached request must still succeed even if the provider is
    # currently unconfigured or unreachable — this check is purely informational.
    quota_warning = None
    try:
        usage = provider.get_usage()
        if (
            usage.character_limit > 0
            and usage.fraction_used >= settings.translation_usage_warn_threshold
        ):
            quota_warning = "Monthly translation quota is almost used up."
    except Exception:  # noqa: BLE001 - deliberately fail open, see docstring above.
        pass

    return TranslateResult(
        selection_translation=selection_translation,
        sentence_translation=sentence_translation,
        quota_warning=quota_warning,
    )
