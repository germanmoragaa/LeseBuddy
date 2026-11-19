import math
import threading
import time
from collections import deque
from collections.abc import Callable, Hashable


class SlidingWindowRateLimiter:
    """Allows at most `limit` hits per key within any rolling `window_seconds`.

    In memory and **single-process only**: with several workers each process keeps its own
    counters (so the effective limit is `limit * workers`), and counters reset on restart.
    That's an accepted trade-off for a soft per-user guard in front of Genius; a shared store
    (e.g. a Postgres table like translation_request_log) is the upgrade path if the app ever
    runs multiple workers.
    """

    def __init__(
        self,
        *,
        limit: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._limit = limit
        self._window_seconds = window_seconds
        self._clock = clock
        self._hits: dict[Hashable, deque[float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: Hashable) -> int | None:
        """Records a hit for `key` and returns None if it's allowed, or the number of whole
        seconds until the next hit would be allowed if the limit is already reached (a
        rejected hit is not recorded)."""
        now = self._clock()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] >= self._window_seconds:
                hits.popleft()
            if len(hits) >= self._limit:
                return max(1, math.ceil(hits[0] + self._window_seconds - now))
            hits.append(now)
            self._prune(now)
            return None

    def _prune(self, now: float) -> None:
        # Keeps memory bounded by currently-active keys rather than every user ever seen.
        stale = [
            key
            for key, hits in self._hits.items()
            if not hits or now - hits[-1] >= self._window_seconds
        ]
        for key in stale:
            del self._hits[key]
