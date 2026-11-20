"""/api/v1/songs endpoints, always against FakeSongProvider (wired in conftest) — tests and
CI never call Genius (ADR 0006)."""

import pytest
from factories import make_user
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api import deps
from app.api.deps import get_song_provider
from app.core.config import Settings
from app.main import app
from app.services.songs.fake_provider import FakeSongProvider
from app.services.songs.genius_provider import GeniusSongProvider
from app.services.songs.provider import (
    NullSongProvider,
    SongsProviderError,
    SongsTimeoutError,
)

VALID_PASSWORD = "correct horse battery staple"


def _login_as(
    client: TestClient,
    db_session: Session,
    *,
    username: str = "alex_morgan",
    email: str = "alex@example.com",
    verified: bool = True,
) -> None:
    make_user(
        db_session,
        email=email,
        username=username,
        password=VALID_PASSWORD,
        email_verified=verified,
    )
    response = client.post(
        "/api/v1/auth/login", json={"identifier": username, "password": VALID_PASSWORD}
    )
    assert response.status_code == 200


class TestSearch:
    def test_returns_results_with_german_songs_first(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session)

        response = client.get("/api/v1/songs/search", params={"q": "nacht"})

        assert response.status_code == 200
        body = response.json()
        assert body["query"] == "nacht"
        # The fake returns the English song first; German results are ranked ahead of it
        # while keeping their own relative order.
        assert [r["genius_id"] for r in body["results"]] == [900001, 900003, 900002]
        assert [r["language"] for r in body["results"]] == ["de", "de", "en"]

    def test_result_shape(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session)

        result = client.get("/api/v1/songs/search", params={"q": "Nachtlicht"}).json()["results"][0]

        assert result == {
            "genius_id": 900001,
            "title": "Nachtlicht",
            "primary_artist": "Die Erfundenen",
            "thumbnail_url": "https://images.example.test/nachtlicht-300x300.jpg",
            "cover_url": "https://images.example.test/nachtlicht-1000x1000.jpg",
            "genius_url": "https://genius.example.test/die-erfundenen-nachtlicht",
            "release_date_display": "May 14, 2021",
            "release_year": 2021,
            "language": "de",
        }

    def test_no_matches_returns_empty_results(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session)

        response = client.get("/api/v1/songs/search", params={"q": "zzzz"})

        assert response.status_code == 200
        assert response.json()["results"] == []

    def test_trims_query_before_searching(
        self, client: TestClient, db_session: Session, fake_song_provider: FakeSongProvider
    ) -> None:
        _login_as(client, db_session)

        response = client.get("/api/v1/songs/search", params={"q": "   nacht  "})

        assert response.status_code == 200
        assert response.json()["query"] == "nacht"
        assert fake_song_provider.search_calls == [("nacht", 10)]

    def test_respects_limit(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session)

        response = client.get("/api/v1/songs/search", params={"q": "nacht", "limit": 1})

        assert len(response.json()["results"]) == 1

    @pytest.mark.parametrize(
        "params",
        [
            {},
            {"q": ""},
            {"q": "a"},
            {"q": "   a   "},
            {"q": "x" * 101},
            {"q": "nacht", "limit": 0},
            {"q": "nacht", "limit": 21},
        ],
    )
    def test_rejects_invalid_params_without_calling_provider(
        self,
        client: TestClient,
        db_session: Session,
        fake_song_provider: FakeSongProvider,
        params: dict[str, object],
    ) -> None:
        _login_as(client, db_session)

        response = client.get("/api/v1/songs/search", params=params)

        assert response.status_code == 422
        assert fake_song_provider.search_calls == []

    def test_accepts_boundary_lengths(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session)

        assert client.get("/api/v1/songs/search", params={"q": "ab"}).status_code == 200
        assert client.get("/api/v1/songs/search", params={"q": "x" * 100}).status_code == 200

    def test_requires_login(self, client: TestClient) -> None:
        assert client.get("/api/v1/songs/search", params={"q": "nacht"}).status_code == 401

    def test_requires_verified_email(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, verified=False)

        response = client.get("/api/v1/songs/search", params={"q": "nacht"})

        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "email_not_verified"


class TestSearchCache:
    def test_repeated_normalized_query_hits_provider_once(
        self, client: TestClient, db_session: Session, fake_song_provider: FakeSongProvider
    ) -> None:
        _login_as(client, db_session)

        first = client.get("/api/v1/songs/search", params={"q": "Nacht"})
        second = client.get("/api/v1/songs/search", params={"q": "  nacht "})

        assert first.json()["results"] == second.json()["results"]
        assert len(fake_song_provider.search_calls) == 1

    def test_cache_is_shared_across_users(
        self, client: TestClient, db_session: Session, fake_song_provider: FakeSongProvider
    ) -> None:
        _login_as(client, db_session)
        client.get("/api/v1/songs/search", params={"q": "nacht"})
        client.post("/api/v1/auth/logout")
        _login_as(client, db_session, username="bailey_jones", email="bailey@example.com")

        client.get("/api/v1/songs/search", params={"q": "nacht"})

        assert len(fake_song_provider.search_calls) == 1

    def test_different_limit_is_a_separate_entry(
        self, client: TestClient, db_session: Session, fake_song_provider: FakeSongProvider
    ) -> None:
        _login_as(client, db_session)

        client.get("/api/v1/songs/search", params={"q": "nacht", "limit": 5})
        client.get("/api/v1/songs/search", params={"q": "nacht", "limit": 10})

        assert len(fake_song_provider.search_calls) == 2

    def test_errors_are_not_cached(
        self, client: TestClient, db_session: Session, fake_song_provider: FakeSongProvider
    ) -> None:
        _login_as(client, db_session)
        fake_song_provider.fail_with = SongsProviderError()
        assert client.get("/api/v1/songs/search", params={"q": "nacht"}).status_code == 502

        fake_song_provider.fail_with = None
        response = client.get("/api/v1/songs/search", params={"q": "nacht"})

        assert response.status_code == 200
        assert len(response.json()["results"]) == 3


class TestSearchRateLimit:
    def test_returns_429_after_30_searches_in_a_minute(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session)
        for _ in range(30):
            assert client.get("/api/v1/songs/search", params={"q": "nacht"}).status_code == 200

        response = client.get("/api/v1/songs/search", params={"q": "nacht"})

        assert response.status_code == 429
        detail = response.json()["detail"]
        assert detail["code"] == "songs_rate_limited"
        assert 1 <= detail["retry_after"] <= 60
        assert response.headers["Retry-After"] == str(detail["retry_after"])

    def test_limit_is_per_user(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session)
        for _ in range(30):
            client.get("/api/v1/songs/search", params={"q": "nacht"})
        client.post("/api/v1/auth/logout")
        _login_as(client, db_session, username="bailey_jones", email="bailey@example.com")

        response = client.get("/api/v1/songs/search", params={"q": "nacht"})

        assert response.status_code == 200


class TestProviderErrors:
    def test_missing_token_returns_503_not_configured(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session)
        app.dependency_overrides[get_song_provider] = NullSongProvider

        search = client.get("/api/v1/songs/search", params={"q": "nacht"})
        song = client.get("/api/v1/songs/genius/900001")

        for response in (search, song):
            assert response.status_code == 503
            assert response.json()["detail"]["code"] == "songs_not_configured"

    def test_timeout_returns_504(
        self, client: TestClient, db_session: Session, fake_song_provider: FakeSongProvider
    ) -> None:
        _login_as(client, db_session)
        fake_song_provider.fail_with = SongsTimeoutError()

        response = client.get("/api/v1/songs/search", params={"q": "nacht"})

        assert response.status_code == 504
        assert response.json()["detail"]["code"] == "songs_timeout"

    def test_provider_error_returns_502(
        self, client: TestClient, db_session: Session, fake_song_provider: FakeSongProvider
    ) -> None:
        _login_as(client, db_session)
        fake_song_provider.fail_with = SongsProviderError()

        response = client.get("/api/v1/songs/genius/900001")

        assert response.status_code == 502
        assert response.json()["detail"]["code"] == "songs_provider_error"


class TestGetGeniusSong:
    def test_returns_full_metadata(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session)

        response = client.get("/api/v1/songs/genius/900001")

        assert response.status_code == 200
        assert response.json() == {
            "genius_id": 900001,
            "title": "Nachtlicht",
            "primary_artist": "Die Erfundenen",
            "album": "Lieder aus Papier",
            "release_date": "2021-05-14",
            "release_date_display": "May 14, 2021",
            "cover_url": "https://images.example.test/nachtlicht-1000x1000.jpg",
            "cover_thumbnail_url": "https://images.example.test/nachtlicht-300x300.jpg",
            "genius_url": "https://genius.example.test/die-erfundenen-nachtlicht",
            "language": "de",
        }

    def test_is_cached(
        self, client: TestClient, db_session: Session, fake_song_provider: FakeSongProvider
    ) -> None:
        _login_as(client, db_session)

        client.get("/api/v1/songs/genius/900001")
        client.get("/api/v1/songs/genius/900001")

        assert fake_song_provider.get_song_calls == [900001]

    def test_unknown_song_returns_404(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session)

        response = client.get("/api/v1/songs/genius/123")

        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "song_not_found"

    @pytest.mark.parametrize("genius_id", ["0", "-5", "abc"])
    def test_rejects_invalid_id(
        self, client: TestClient, db_session: Session, genius_id: str
    ) -> None:
        _login_as(client, db_session)

        assert client.get(f"/api/v1/songs/genius/{genius_id}").status_code == 422

    def test_requires_login(self, client: TestClient) -> None:
        assert client.get("/api/v1/songs/genius/900001").status_code == 401


class TestProviderSelection:
    def test_empty_token_selects_null_provider(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            deps, "get_settings", lambda: Settings(_env_file=None, genius_access_token="")
        )

        assert isinstance(deps.get_song_provider(), NullSongProvider)

    def test_token_selects_genius_provider(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            deps,
            "get_settings",
            lambda: Settings(_env_file=None, genius_access_token="test-token-not-real"),
        )

        assert isinstance(deps.get_song_provider(), GeniusSongProvider)
