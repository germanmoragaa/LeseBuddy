from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import StringConstraints
from sqlalchemy.orm import Session

from app.api.articles import to_article_read
from app.api.deps import (
    get_current_verified_user,
    get_song_cache,
    get_song_provider,
    get_song_search_rate_limiter,
)
from app.core.db import get_db
from app.models import User
from app.schemas.article import ArticleRead
from app.schemas.song import GeniusSongRead, SongCreate, SongSearchResponse, SongSearchResultRead
from app.services.songs.cache import TTLCache
from app.services.songs.library import (
    LyricsEmptyError,
    SongAlreadySavedError,
    save_genius_song,
)
from app.services.songs.provider import (
    SongNotFoundError,
    SongProvider,
    SongsNotConfiguredError,
    SongsProviderError,
    SongsTimeoutError,
)
from app.services.songs.rate_limit import SlidingWindowRateLimiter
from app.services.songs.service import (
    SongSearchRateLimitedError,
    get_song_metadata,
    search_songs,
)

router = APIRouter(prefix="/api/v1/songs", tags=["songs"])

SEARCH_QUERY_MIN_LENGTH = 2
SEARCH_QUERY_MAX_LENGTH = 100
SEARCH_LIMIT_MAX = 20

# Trimmed *before* the length check, so "  a  " is rejected as too short.
SearchQuery = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=SEARCH_QUERY_MIN_LENGTH,
        max_length=SEARCH_QUERY_MAX_LENGTH,
    ),
]


@contextmanager
def _provider_errors_as_http() -> Iterator[None]:
    """Maps every typed provider error to a clean JSON error — a provider failure must never
    surface as a 500."""
    try:
        yield
    except SongsNotConfiguredError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "songs_not_configured",
                "message": "Song search isn't configured yet.",
            },
        ) from None
    except SongNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "song_not_found", "message": "That song wasn't found on Genius."},
        ) from None
    except SongsTimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={
                "code": "songs_timeout",
                "message": "Genius took too long to respond. Please try again.",
            },
        ) from None
    except SongsProviderError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "songs_provider_error",
                "message": "Song search is unavailable right now.",
            },
        ) from None


@router.get("/search", response_model=SongSearchResponse)
def search(
    q: Annotated[SearchQuery, Query()],
    limit: int = Query(default=10, ge=1, le=SEARCH_LIMIT_MAX),
    user: User = Depends(get_current_verified_user),
    provider: SongProvider = Depends(get_song_provider),
    cache: TTLCache = Depends(get_song_cache),
    rate_limiter: SlidingWindowRateLimiter = Depends(get_song_search_rate_limiter),
) -> SongSearchResponse:
    try:
        with _provider_errors_as_http():
            results = search_songs(
                provider, cache, rate_limiter, user_key=user.id, query=q, limit=limit
            )
    except SongSearchRateLimitedError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "songs_rate_limited",
                "message": "Too many song searches. Please wait a moment.",
                "retry_after": exc.retry_after,
            },
            headers={"Retry-After": str(exc.retry_after)},
        ) from None

    return SongSearchResponse(
        query=q, results=[SongSearchResultRead.model_validate(result) for result in results]
    )


@router.get("/genius/{genius_id}", response_model=GeniusSongRead)
def get_genius_song(
    genius_id: Annotated[int, Path(gt=0)],
    user: User = Depends(get_current_verified_user),
    provider: SongProvider = Depends(get_song_provider),
    cache: TTLCache = Depends(get_song_cache),
) -> GeniusSongRead:
    with _provider_errors_as_http():
        song = get_song_metadata(provider, cache, genius_id)
    return GeniusSongRead.model_validate(song)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ArticleRead)
def save_song(
    data: SongCreate,
    user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
    provider: SongProvider = Depends(get_song_provider),
    cache: TTLCache = Depends(get_song_cache),
) -> ArticleRead:
    """Saves a Genius song with lyrics the user pasted themselves into their private
    library, as a kind="song" article. Lyrics are never fetched from anywhere."""
    try:
        with _provider_errors_as_http():
            article = save_genius_song(
                db,
                user,
                provider,
                cache,
                genius_id=data.genius_song_id,
                lyrics_text=data.lyrics_text,
            )
    except LyricsEmptyError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "lyrics_empty",
                "message": "Paste the song's lyrics - only lyrics-page leftovers were found.",
            },
        ) from None
    except SongAlreadySavedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "song_already_saved",
                "message": "This song is already in your library.",
                "article_id": str(exc.article_id),
            },
        ) from None
    return to_article_read(article)
