"""The only seam song-metadata code goes through (ADR 0006).

A provider returns *metadata only* — title, artist, album, dates, cover/page URLs, language.
No provider ever returns or fetches lyrics; lyrics are always pasted by the user.
"""

from dataclasses import dataclass
from datetime import date
from typing import Protocol


class SongsNotConfiguredError(Exception):
    """No provider token is configured, or the configured token was rejected."""


class SongsTimeoutError(Exception):
    """The provider didn't respond in time."""


class SongsProviderError(Exception):
    """Any other provider-side failure: bad status, network error, unexpected payload."""


class SongNotFoundError(Exception):
    """The provider has no song with the requested id."""


@dataclass(frozen=True)
class SongSearchResult:
    genius_id: int
    title: str
    primary_artist: str
    thumbnail_url: str | None
    cover_url: str | None
    genius_url: str | None
    release_date_display: str | None
    release_year: int | None
    # ISO 639-1 code when the provider knows it (Genius: e.g. "de", "en"); None otherwise.
    language: str | None


@dataclass(frozen=True)
class SongMetadata:
    genius_id: int
    title: str
    primary_artist: str
    album: str | None
    release_date: date | None
    release_date_display: str | None
    cover_url: str | None
    genius_url: str | None
    language: str | None


class SongProvider(Protocol):
    def search(self, query: str, limit: int) -> list[SongSearchResult]: ...

    def get_song(self, genius_id: int) -> SongMetadata: ...


class NullSongProvider:
    """Returned when `GENIUS_ACCESS_TOKEN` is empty — the app still starts; any song lookup
    raises the same typed error a real provider raises for a rejected token."""

    def search(self, query: str, limit: int) -> list[SongSearchResult]:
        raise SongsNotConfiguredError

    def get_song(self, genius_id: int) -> SongMetadata:
        raise SongsNotConfiguredError
