"""GeniusSongProvider parsing and error mapping, entirely through httpx.MockTransport — no
request in this file ever leaves the process. Fixture JSON mirrors the real Genius response
shape with invented songs (ADR 0006)."""

import json
from datetime import date
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.services.songs.genius_provider import GENIUS_API_BASE_URL, GeniusSongProvider
from app.services.songs.provider import (
    SongNotFoundError,
    SongsNotConfiguredError,
    SongsProviderError,
    SongsTimeoutError,
)

FIXTURES = Path(__file__).parent / "fixtures" / "genius"
TOKEN = "test-token-not-a-real-secret"


def _fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class Recorder:
    def __init__(self, handler: Any) -> None:
        self.handler = handler
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.handler(request)


def _provider(handler: Any) -> tuple[GeniusSongProvider, Recorder]:
    recorder = Recorder(handler)
    return GeniusSongProvider(TOKEN, transport=httpx.MockTransport(recorder)), recorder


def _json(body: Any, status_code: int = 200) -> Any:
    return lambda request: httpx.Response(status_code, json=body)


class TestSearch:
    def test_parses_hits_in_provider_order(self) -> None:
        provider, _ = _provider(_json(_fixture("search.json")))

        results = provider.search("nacht", 10)

        assert [r.genius_id for r in results] == [900002, 900001, 900004]
        night_light, nachtlicht, _ = results
        assert nachtlicht.title == "Nachtlicht"
        assert nachtlicht.primary_artist == "Die Erfundenen"
        assert nachtlicht.thumbnail_url == "https://images.example.test/nachtlicht-300x300.jpg"
        assert nachtlicht.cover_url == "https://images.example.test/nachtlicht-1000x1000.jpg"
        assert nachtlicht.genius_url == (
            "https://genius.example.test/die-erfundenen-nachtlicht-lyrics"
        )
        assert nachtlicht.release_date_display == "May 14, 2021"
        assert nachtlicht.release_year == 2021
        assert nachtlicht.language == "de"
        assert night_light.language == "en"
        assert night_light.release_year == 2019

    def test_falls_back_for_sparse_hits(self) -> None:
        provider, _ = _provider(_json(_fixture("search.json")))

        sparse = provider.search("sommer", 10)[2]

        # Empty primary_artist.name -> artist_names; no song art -> header thumbnail.
        assert sparse.primary_artist == "Kapelle Ohnenamen"
        assert sparse.thumbnail_url == (
            "https://images.example.test/sommerregen-header-300x300.jpg"
        )
        assert sparse.cover_url is None
        assert sparse.release_date_display is None
        assert sparse.release_year is None
        assert sparse.language is None

    def test_sends_bearer_token_to_the_official_search_endpoint_only(self) -> None:
        provider, recorder = _provider(_json(_fixture("search.json")))

        provider.search("Nachtlicht", 5)

        (request,) = recorder.requests
        assert request.method == "GET"
        assert str(request.url).startswith(f"{GENIUS_API_BASE_URL}/search?")
        assert request.url.host == "api.genius.com"
        assert request.url.params["q"] == "Nachtlicht"
        assert request.url.params["per_page"] == "5"
        assert request.headers["Authorization"] == f"Bearer {TOKEN}"

    def test_caps_per_page_and_truncates_to_limit(self) -> None:
        provider, recorder = _provider(_json(_fixture("search.json")))

        results = provider.search("nacht", 2)
        provider.search("nacht", 50)

        assert len(results) == 2
        assert recorder.requests[1].url.params["per_page"] == "20"

    def test_ignores_non_song_hits(self) -> None:
        body = _fixture("search.json")
        body["response"]["hits"][0]["type"] = "article"
        provider, _ = _provider(_json(body))

        assert [r.genius_id for r in provider.search("nacht", 10)] == [900001, 900004]

    def test_empty_hits_returns_empty_list(self) -> None:
        provider, _ = _provider(_json({"meta": {"status": 200}, "response": {"hits": []}}))

        assert provider.search("zzzz", 10) == []


class TestGetSong:
    def test_parses_full_metadata(self) -> None:
        provider, recorder = _provider(_json(_fixture("song.json")))

        song = provider.get_song(900001)

        assert song.genius_id == 900001
        assert song.title == "Nachtlicht"
        assert song.primary_artist == "Die Erfundenen"
        assert song.album == "Lieder aus Papier"
        assert song.release_date == date(2021, 5, 14)
        assert song.release_date_display == "May 14, 2021"
        assert song.cover_url == "https://images.example.test/nachtlicht-1000x1000.jpg"
        assert song.genius_url == "https://genius.example.test/die-erfundenen-nachtlicht-lyrics"
        assert song.language == "de"
        (request,) = recorder.requests
        assert request.url.path == "/songs/900001"
        assert request.url.host == "api.genius.com"

    def test_missing_album_and_partial_date(self) -> None:
        body = _fixture("song.json")
        body["response"]["song"]["album"] = None
        body["response"]["song"]["release_date"] = "2021"
        body["response"]["song"]["release_date_for_display"] = "2021"
        provider, _ = _provider(_json(body))

        song = provider.get_song(900001)

        assert song.album is None
        assert song.release_date is None
        assert song.release_date_display == "2021"

    def test_never_exposes_lyrics_or_embed_content(self) -> None:
        provider, _ = _provider(_json(_fixture("song.json")))

        song = provider.get_song(900001)

        assert not hasattr(song, "lyrics")
        assert not hasattr(song, "embed_content")


class TestErrorMapping:
    def test_timeout_maps_to_songs_timeout_error(self) -> None:
        def raise_timeout(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timed out", request=request)

        provider, _ = _provider(raise_timeout)

        with pytest.raises(SongsTimeoutError):
            provider.search("nacht", 10)

    def test_connection_error_maps_to_provider_error(self) -> None:
        def refuse(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("refused", request=request)

        provider, _ = _provider(refuse)

        with pytest.raises(SongsProviderError):
            provider.search("nacht", 10)

    def test_401_maps_to_not_configured(self) -> None:
        provider, _ = _provider(_json({"error": "invalid_token"}, status_code=401))

        with pytest.raises(SongsNotConfiguredError):
            provider.search("nacht", 10)

    def test_404_on_song_maps_to_not_found(self) -> None:
        provider, _ = _provider(_json({"meta": {"status": 404}}, status_code=404))

        with pytest.raises(SongNotFoundError):
            provider.get_song(123)

    @pytest.mark.parametrize("status_code", [403, 429, 500, 503])
    def test_other_http_errors_map_to_provider_error(self, status_code: int) -> None:
        provider, _ = _provider(_json({"meta": {"status": status_code}}, status_code))

        with pytest.raises(SongsProviderError):
            provider.search("nacht", 10)

    def test_redirect_is_not_followed(self) -> None:
        provider, recorder = _provider(
            lambda request: httpx.Response(
                302, headers={"Location": "https://genius.com/some-lyrics-page"}
            )
        )

        with pytest.raises(SongsProviderError):
            provider.search("nacht", 10)
        assert len(recorder.requests) == 1

    def test_non_json_body_maps_to_provider_error(self) -> None:
        provider, _ = _provider(lambda request: httpx.Response(200, text="<html>nope</html>"))

        with pytest.raises(SongsProviderError):
            provider.search("nacht", 10)

    @pytest.mark.parametrize(
        "body",
        [
            {"meta": {"status": 200}},
            {"response": None},
            {"response": {"hits": "not-a-list"}},
            {"response": {"hits": [{"type": "song", "result": {"id": "x", "title": "T"}}]}},
            {"response": {"hits": [{"type": "song", "result": {"id": 1, "title": ""}}]}},
        ],
    )
    def test_malformed_search_payload_maps_to_provider_error(self, body: Any) -> None:
        provider, _ = _provider(_json(body))

        with pytest.raises(SongsProviderError):
            provider.search("nacht", 10)

    def test_malformed_song_payload_maps_to_provider_error(self) -> None:
        provider, _ = _provider(_json({"response": {"song": {"id": 1}}}))

        with pytest.raises(SongsProviderError):
            provider.get_song(1)
