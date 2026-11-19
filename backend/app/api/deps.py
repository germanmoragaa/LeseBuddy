from collections.abc import Callable
from datetime import UTC, datetime
from functools import lru_cache

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import SESSION_COOKIE_NAME
from app.models import User
from app.services.auth_service import get_user_for_token
from app.services.email import EmailSender, SmtpEmailSender
from app.services.songs.cache import TTLCache
from app.services.songs.genius_provider import GeniusSongProvider
from app.services.songs.provider import NullSongProvider, SongProvider
from app.services.songs.rate_limit import SlidingWindowRateLimiter
from app.services.translation.deepl_provider import DeepLTranslationProvider
from app.services.translation.provider import NullTranslationProvider, TranslationProvider


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    raw_token = request.cookies.get(SESSION_COOKIE_NAME)
    if raw_token is not None:
        user = get_user_for_token(db, raw_token)
        if user is not None:
            return user

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def get_current_verified_user(user: User = Depends(get_current_user)) -> User:
    if user.email_verified_at is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "email_not_verified",
                "message": "Please verify your email address to continue.",
            },
        )
    return user


def get_email_sender() -> EmailSender:
    return SmtpEmailSender(get_settings())


def get_translation_provider() -> TranslationProvider:
    settings = get_settings()
    if not settings.deepl_api_key:
        return NullTranslationProvider()
    return DeepLTranslationProvider(settings)


def get_song_provider() -> SongProvider:
    settings = get_settings()
    if not settings.genius_access_token:
        return NullSongProvider()
    return GeniusSongProvider(settings.genius_access_token)


SONG_CACHE_MAX_ENTRIES = 1000


@lru_cache
def get_song_cache() -> TTLCache:
    """Process-wide singleton (lru_cache), so cached results outlive a single request."""
    return TTLCache(
        ttl_seconds=get_settings().songs_cache_ttl_seconds, max_entries=SONG_CACHE_MAX_ENTRIES
    )


@lru_cache
def get_song_search_rate_limiter() -> SlidingWindowRateLimiter:
    """Process-wide singleton — see SlidingWindowRateLimiter for the single-process caveat."""
    return SlidingWindowRateLimiter(
        limit=get_settings().songs_search_rate_limit_per_minute, window_seconds=60
    )


def get_clock() -> Callable[[], datetime]:
    """Returns a zero-arg "now" getter rather than a fixed value, so tests can override this
    dependency once per request with a fixed instant instead of needing to freeze real time."""
    return lambda: datetime.now(UTC)
