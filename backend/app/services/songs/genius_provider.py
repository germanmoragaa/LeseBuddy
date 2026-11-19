"""Genius official API client — search and song metadata only (ADR 0006).

Talks exclusively to https://api.genius.com, and only to GET /search and GET /songs/{id}.
It never requests genius.com web pages and never fetches lyrics: the official API doesn't
return them, and scraping them is exactly what ADR 0006 rules out. Redirects are not
followed, so a response can never bounce this client onto a web page either.
"""

import logging
import time
from datetime import date
from typing import Any

import httpx

from app.services.songs.provider import (
    SongMetadata,
    SongNotFoundError,
    SongSearchResult,
    SongsNotConfiguredError,
    SongsProviderError,
    SongsTimeoutError,
)

logger = logging.getLogger(__name__)

GENIUS_API_BASE_URL = "https://api.genius.com"
GENIUS_TIMEOUT_SECONDS = 5.0
# Genius' /search caps per_page at 20.
GENIUS_SEARCH_MAX_PER_PAGE = 20


class GeniusSongProvider:
    """Never logs the token or the search text — only status, result counts and latency."""

    def __init__(
        self,
        access_token: str,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout_seconds: float = GENIUS_TIMEOUT_SECONDS,
    ) -> None:
        self._access_token = access_token
        # Injectable so tests can use httpx.MockTransport — no network in tests or CI.
        self._transport = transport
        self._timeout_seconds = timeout_seconds

    def search(self, query: str, limit: int) -> list[SongSearchResult]:
        per_page = max(1, min(limit, GENIUS_SEARCH_MAX_PER_PAGE))
        payload = self._get("/search", {"q": query, "per_page": per_page})
        try:
            hits = payload["hits"]
            results = [
                _parse_search_hit(hit["result"]) for hit in hits if hit.get("type") == "song"
            ]
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            raise SongsProviderError("unexpected Genius search payload") from exc
        return results[:limit]

    def get_song(self, genius_id: int) -> SongMetadata:
        payload = self._get(f"/songs/{int(genius_id)}", {"text_format": "plain"})
        try:
            return _parse_song(payload["song"])
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            raise SongsProviderError("unexpected Genius song payload") from exc

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        started = time.monotonic()
        try:
            with httpx.Client(
                base_url=GENIUS_API_BASE_URL,
                headers={
                    "Authorization": f"Bearer {self._access_token}",
                    "Accept": "application/json",
                },
                timeout=self._timeout_seconds,
                follow_redirects=False,
                transport=self._transport,
            ) as client:
                response = client.get(path, params=params)
        except httpx.TimeoutException as exc:
            raise SongsTimeoutError from exc
        except httpx.HTTPError as exc:
            raise SongsProviderError("could not reach Genius") from exc

        elapsed_ms = (time.monotonic() - started) * 1000
        endpoint = "search" if path == "/search" else "song"
        logger.info(
            "genius %s: status=%d latency_ms=%.0f", endpoint, response.status_code, elapsed_ms
        )

        if response.status_code == 401:
            raise SongsNotConfiguredError
        if response.status_code == 404:
            raise SongNotFoundError
        if response.status_code != 200:
            raise SongsProviderError(f"Genius returned status {response.status_code}")

        try:
            body = response.json()
            inner = body["response"]
        except (ValueError, KeyError, TypeError) as exc:
            raise SongsProviderError("Genius returned a malformed body") from exc
        if not isinstance(inner, dict):
            raise SongsProviderError("Genius returned a malformed body")
        return inner


def _optional_str(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _required_str(value: Any) -> str:
    result = _optional_str(value)
    if result is None:
        raise ValueError("missing required string")
    return result


def _required_id(value: Any) -> int:
    # bool is an int subclass — never a valid id.
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError("missing or invalid id")
    return value


def _primary_artist_name(song: dict[str, Any]) -> str:
    artist = song.get("primary_artist")
    if isinstance(artist, dict) and _optional_str(artist.get("name")):
        return _required_str(artist["name"])
    # Older/partial payloads only carry the combined display string.
    return _required_str(song.get("artist_names"))


def _release_year(song: dict[str, Any]) -> int | None:
    components = song.get("release_date_components")
    if isinstance(components, dict):
        year = components.get("year")
        if isinstance(year, int) and not isinstance(year, bool):
            return year
    return None


def _release_date(song: dict[str, Any]) -> date | None:
    raw = _optional_str(song.get("release_date"))
    if raw is None:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        # Genius sometimes has only a partial date; release_date_display still carries it.
        return None


def _parse_search_hit(song: dict[str, Any]) -> SongSearchResult:
    return SongSearchResult(
        genius_id=_required_id(song.get("id")),
        title=_required_str(song.get("title")),
        primary_artist=_primary_artist_name(song),
        thumbnail_url=_optional_str(song.get("song_art_image_thumbnail_url"))
        or _optional_str(song.get("header_image_thumbnail_url")),
        cover_url=_optional_str(song.get("song_art_image_url")),
        genius_url=_optional_str(song.get("url")),
        release_date_display=_optional_str(song.get("release_date_for_display")),
        release_year=_release_year(song),
        language=_optional_str(song.get("language")),
    )


def _parse_song(song: dict[str, Any]) -> SongMetadata:
    album = song.get("album")
    return SongMetadata(
        genius_id=_required_id(song.get("id")),
        title=_required_str(song.get("title")),
        primary_artist=_primary_artist_name(song),
        album=_optional_str(album.get("name")) if isinstance(album, dict) else None,
        release_date=_release_date(song),
        release_date_display=_optional_str(song.get("release_date_for_display")),
        cover_url=_optional_str(song.get("song_art_image_url")),
        genius_url=_optional_str(song.get("url")),
        language=_optional_str(song.get("language")),
    )
