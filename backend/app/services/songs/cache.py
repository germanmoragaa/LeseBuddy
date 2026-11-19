import threading
import time
from collections import OrderedDict
from collections.abc import Callable, Hashable
from typing import Any

# Sentinel distinguishing "not cached" from a cached falsy value (e.g. an empty result list).
MISSING: Any = object()


class TTLCache:
    """Small in-memory cache with per-entry expiry and LRU eviction once `max_entries` is
    reached. Thread-safe, since FastAPI runs sync endpoints in a thread pool.

    Single-process only: each worker process has its own copy, and everything is lost on
    restart — acceptable for a cache whose only job is sparing duplicate provider calls.
    """

    def __init__(
        self,
        *,
        ttl_seconds: float,
        max_entries: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._clock = clock
        self._entries: OrderedDict[Hashable, tuple[float, Any]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: Hashable) -> Any:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return MISSING
            expires_at, value = entry
            if self._clock() >= expires_at:
                del self._entries[key]
                return MISSING
            self._entries.move_to_end(key)
            return value

    def set(self, key: Hashable, value: Any) -> None:
        with self._lock:
            self._entries[key] = (self._clock() + self._ttl_seconds, value)
            self._entries.move_to_end(key)
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)
