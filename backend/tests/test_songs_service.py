"""Pure unit tests for the song cache, rate limiter and ranking — injected clocks, no DB,
no network."""

from app.services.songs.cache import MISSING, TTLCache
from app.services.songs.provider import SongSearchResult
from app.services.songs.rate_limit import SlidingWindowRateLimiter
from app.services.songs.service import normalize_query, rank_german_first


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def _result(genius_id: int, language: str | None) -> SongSearchResult:
    return SongSearchResult(
        genius_id=genius_id,
        title=f"Song {genius_id}",
        primary_artist="Die Erfundenen",
        thumbnail_url=None,
        cover_url=None,
        genius_url=None,
        release_date_display=None,
        release_year=None,
        language=language,
    )


class TestTTLCache:
    def test_returns_value_until_ttl_expires(self) -> None:
        clock = FakeClock()
        cache = TTLCache(ttl_seconds=600, max_entries=10, clock=clock)
        cache.set("k", [1])

        clock.now += 599
        assert cache.get("k") == [1]
        clock.now += 1
        assert cache.get("k") is MISSING
        assert len(cache) == 0

    def test_caches_falsy_values(self) -> None:
        cache = TTLCache(ttl_seconds=600, max_entries=10)
        cache.set("empty", [])

        assert cache.get("empty") == []

    def test_evicts_least_recently_used_beyond_max_entries(self) -> None:
        cache = TTLCache(ttl_seconds=600, max_entries=2)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.get("a")  # "b" is now least recently used

        cache.set("c", 3)

        assert len(cache) == 2
        assert cache.get("b") is MISSING
        assert cache.get("a") == 1
        assert cache.get("c") == 3


class TestSlidingWindowRateLimiter:
    def test_allows_up_to_limit_then_reports_retry_after(self) -> None:
        clock = FakeClock()
        limiter = SlidingWindowRateLimiter(limit=3, window_seconds=60, clock=clock)

        assert [limiter.hit("u") for _ in range(3)] == [None, None, None]
        clock.now += 20
        assert limiter.hit("u") == 40

    def test_window_slides(self) -> None:
        clock = FakeClock()
        limiter = SlidingWindowRateLimiter(limit=2, window_seconds=60, clock=clock)
        limiter.hit("u")
        clock.now += 30
        limiter.hit("u")
        assert limiter.hit("u") is not None

        clock.now += 30  # the first hit has now left the window
        assert limiter.hit("u") is None
        assert limiter.hit("u") is not None

    def test_rejected_hits_are_not_recorded(self) -> None:
        clock = FakeClock()
        limiter = SlidingWindowRateLimiter(limit=1, window_seconds=60, clock=clock)
        limiter.hit("u")
        for _ in range(5):
            limiter.hit("u")

        clock.now += 60
        assert limiter.hit("u") is None

    def test_keys_are_independent(self) -> None:
        limiter = SlidingWindowRateLimiter(limit=1, window_seconds=60)

        assert limiter.hit("alice") is None
        assert limiter.hit("bob") is None
        assert limiter.hit("alice") is not None

    def test_retry_after_is_at_least_one_second(self) -> None:
        clock = FakeClock()
        limiter = SlidingWindowRateLimiter(limit=1, window_seconds=60, clock=clock)
        limiter.hit("u")
        clock.now += 59.9

        assert limiter.hit("u") == 1

    def test_prunes_idle_keys(self) -> None:
        clock = FakeClock()
        limiter = SlidingWindowRateLimiter(limit=5, window_seconds=60, clock=clock)
        for user in range(100):
            limiter.hit(user)

        clock.now += 61
        limiter.hit("active")

        assert set(limiter._hits) == {"active"}


class TestRanking:
    def test_german_first_preserving_relative_order(self) -> None:
        results = [_result(1, "en"), _result(2, "de"), _result(3, None), _result(4, "de")]

        ranked = rank_german_first(results)

        assert [r.genius_id for r in ranked] == [2, 4, 1, 3]

    def test_normalize_query(self) -> None:
        assert normalize_query("  Nacht   LICHT ") == "nacht licht"
        assert normalize_query("Straße") == normalize_query("STRASSE")
