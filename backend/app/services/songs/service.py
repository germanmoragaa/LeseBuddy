from collections.abc import Hashable

from app.services.songs.cache import MISSING, TTLCache
from app.services.songs.provider import SongMetadata, SongProvider, SongSearchResult
from app.services.songs.rate_limit import SlidingWindowRateLimiter

GERMAN = "de"


class SongSearchRateLimitedError(Exception):
    def __init__(self, retry_after: int) -> None:
        super().__init__(f"song search rate limited, retry after {retry_after}s")
        self.retry_after = retry_after


def normalize_query(query: str) -> str:
    """Case- and whitespace-insensitive cache key: "  Nacht   LICHT " == "nacht licht"."""
    return " ".join(query.split()).casefold()


def rank_german_first(results: list[SongSearchResult]) -> list[SongSearchResult]:
    """Stable: German songs move to the front, everything else keeps the provider's order.
    Songs with no known language are treated as non-German."""
    return sorted(results, key=lambda result: result.language != GERMAN)


def search_songs(
    provider: SongProvider,
    cache: TTLCache,
    rate_limiter: SlidingWindowRateLimiter,
    *,
    user_key: Hashable,
    query: str,
    limit: int,
) -> list[SongSearchResult]:
    # Every search request counts toward the limit, cached or not: it guards this endpoint
    # (one request per debounced keystroke pause), not just Genius' quota.
    retry_after = rate_limiter.hit(user_key)
    if retry_after is not None:
        raise SongSearchRateLimitedError(retry_after)

    cache_key = ("search", normalize_query(query), limit)
    cached = cache.get(cache_key)
    if cached is not MISSING:
        return cached

    results = rank_german_first(provider.search(query.strip(), limit))
    # Errors raise before this line, so failures are never cached.
    cache.set(cache_key, results)
    return results


def get_song_metadata(provider: SongProvider, cache: TTLCache, genius_id: int) -> SongMetadata:
    cache_key = ("song", genius_id)
    cached = cache.get(cache_key)
    if cached is not MISSING:
        return cached

    song = provider.get_song(genius_id)
    cache.set(cache_key, song)
    return song
