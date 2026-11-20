"""POST /api/v1/songs — saving a Genius song with user-pasted lyrics, always against
FakeSongProvider (no network). Lyrics here are invented lyric-style lines (ADR 0006)."""

import unicodedata

import pytest
from factories import make_song, make_user
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_song_provider
from app.main import app
from app.models import Article, Song, User
from app.services.songs import library
from app.services.songs.fake_provider import FakeSongProvider
from app.services.songs.provider import NullSongProvider, SongsTimeoutError

VALID_PASSWORD = "correct horse battery staple"
LYRICS = "[Hook]\nIch lauf' durch die Nacht\nUnd die Stadt ist noch wach"


def _login_as(
    client: TestClient,
    db_session: Session,
    *,
    username: str = "alex_morgan",
    email: str = "alex@example.com",
    verified: bool = True,
) -> User:
    user = make_user(
        db_session, email=email, username=username, password=VALID_PASSWORD, email_verified=verified
    )
    response = client.post(
        "/api/v1/auth/login", json={"identifier": username, "password": VALID_PASSWORD}
    )
    assert response.status_code == 200
    return user


def _article_count(db_session: Session) -> int:
    return db_session.scalar(select(func.count()).select_from(Article))


class TestSaveSong:
    def test_creates_song_article_with_metadata_from_provider(
        self, client: TestClient, db_session: Session
    ) -> None:
        user = _login_as(client, db_session)

        response = client.post(
            "/api/v1/songs", json={"genius_song_id": 900001, "lyrics_text": LYRICS}
        )

        assert response.status_code == 201
        body = response.json()
        assert body["kind"] == "song"
        assert body["title"] == "Nachtlicht"
        assert body["original_text"] == LYRICS
        assert body["song"] == {
            "title": "Nachtlicht",
            "primary_artist": "Die Erfundenen",
            "album": "Lieder aus Papier",
            "release_date": "2021-05-14",
            "release_date_display": "May 14, 2021",
            "cover_url": "https://images.example.test/nachtlicht-1000x1000.jpg",
            "cover_thumbnail_url": "https://images.example.test/nachtlicht-300x300.jpg",
            "genius_url": "https://genius.example.test/die-erfundenen-nachtlicht",
        }
        song = db_session.scalar(select(Song).where(Song.user_id == user.id))
        assert song is not None
        assert song.genius_song_id == 900001
        assert song.metadata_fetched_at is not None

    def test_ignores_client_sent_metadata(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session)

        response = client.post(
            "/api/v1/songs",
            json={
                "genius_song_id": 900001,
                "lyrics_text": LYRICS,
                "title": "Something else",
                "primary_artist": "Someone else",
                "cover_url": "https://evil.example.test/cover.jpg",
            },
        )

        assert response.status_code == 201
        assert response.json()["title"] == "Nachtlicht"
        assert response.json()["song"]["primary_artist"] == "Die Erfundenen"
        assert response.json()["song"]["cover_url"].startswith("https://images.example.test/")

    def test_normalizes_lyrics_to_nfc(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session)
        decomposed = unicodedata.normalize("NFD", "Für dich lauf' ich durch die Straßen")

        response = client.post(
            "/api/v1/songs", json={"genius_song_id": 900001, "lyrics_text": decomposed}
        )

        assert response.json()["original_text"] == unicodedata.normalize("NFC", decomposed)

    def test_saved_song_is_readable_and_listed(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session)
        created = client.post(
            "/api/v1/songs", json={"genius_song_id": 900001, "lyrics_text": LYRICS}
        ).json()

        detail = client.get(f"/api/v1/articles/{created['id']}").json()
        items = client.get("/api/v1/articles").json()["items"]

        assert detail["kind"] == "song"
        assert [item["id"] for item in items] == [created["id"]]
        assert items[0]["song"]["title"] == "Nachtlicht"

    def test_same_song_twice_returns_409_with_existing_article(
        self, client: TestClient, db_session: Session, fake_song_provider: FakeSongProvider
    ) -> None:
        _login_as(client, db_session)
        first = client.post(
            "/api/v1/songs", json={"genius_song_id": 900001, "lyrics_text": LYRICS}
        ).json()

        response = client.post(
            "/api/v1/songs", json={"genius_song_id": 900001, "lyrics_text": "Andere Zeilen"}
        )

        assert response.status_code == 409
        detail = response.json()["detail"]
        assert detail["code"] == "song_already_saved"
        assert detail["article_id"] == first["id"]
        assert _article_count(db_session) == 1
        # The duplicate is caught before asking the provider again.
        assert fake_song_provider.get_song_calls == [900001]

    def test_different_users_can_save_the_same_song(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session)
        client.post("/api/v1/songs", json={"genius_song_id": 900001, "lyrics_text": LYRICS})
        client.post("/api/v1/auth/logout")
        _login_as(client, db_session, username="bailey_jones", email="bailey@example.com")

        response = client.post(
            "/api/v1/songs", json={"genius_song_id": 900001, "lyrics_text": LYRICS}
        )

        assert response.status_code == 201

    def test_concurrent_duplicate_maps_to_409_not_500(
        self,
        client: TestClient,
        db_session: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        user = _login_as(client, db_session)
        existing = make_song(db_session, user, genius_song_id=900001)
        # Commit so the request's rollback (savepoint) can't discard the competing row.
        db_session.commit()
        real_find = library.find_saved_song_article_id
        calls = {"n": 0}

        def find_missing_first_time(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
            calls["n"] += 1
            # Simulate the race: the other request's row isn't visible at pre-check time.
            return None if calls["n"] == 1 else real_find(*args, **kwargs)

        monkeypatch.setattr(library, "find_saved_song_article_id", find_missing_first_time)

        response = client.post(
            "/api/v1/songs", json={"genius_song_id": 900001, "lyrics_text": LYRICS}
        )

        assert response.status_code == 409
        assert response.json()["detail"]["article_id"] == str(existing.id)


class TestSaveSongErrors:
    def test_unknown_genius_song_returns_404_and_creates_nothing(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session)

        response = client.post("/api/v1/songs", json={"genius_song_id": 123, "lyrics_text": LYRICS})

        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "song_not_found"
        assert _article_count(db_session) == 0

    def test_not_configured_returns_503_and_creates_nothing(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session)
        app.dependency_overrides[get_song_provider] = NullSongProvider

        response = client.post(
            "/api/v1/songs", json={"genius_song_id": 900001, "lyrics_text": LYRICS}
        )

        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "songs_not_configured"
        assert _article_count(db_session) == 0

    def test_timeout_returns_504(
        self, client: TestClient, db_session: Session, fake_song_provider: FakeSongProvider
    ) -> None:
        _login_as(client, db_session)
        fake_song_provider.fail_with = SongsTimeoutError()

        response = client.post(
            "/api/v1/songs", json={"genius_song_id": 900001, "lyrics_text": LYRICS}
        )

        assert response.status_code == 504

    @pytest.mark.parametrize(
        "payload",
        [
            {"genius_song_id": 900001},
            {"genius_song_id": 900001, "lyrics_text": ""},
            {"genius_song_id": 900001, "lyrics_text": "   \n  "},
            {"genius_song_id": 900001, "lyrics_text": "a" * 50_001},
            {"genius_song_id": 0, "lyrics_text": LYRICS},
            {"lyrics_text": LYRICS},
        ],
    )
    def test_rejects_invalid_payload(
        self,
        client: TestClient,
        db_session: Session,
        fake_song_provider: FakeSongProvider,
        payload: dict[str, object],
    ) -> None:
        _login_as(client, db_session)

        response = client.post("/api/v1/songs", json=payload)

        assert response.status_code == 422
        assert fake_song_provider.get_song_calls == []

    def test_requires_login(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/songs", json={"genius_song_id": 900001, "lyrics_text": LYRICS}
        )

        assert response.status_code == 401

    def test_requires_verified_email(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, verified=False)

        response = client.post(
            "/api/v1/songs", json={"genius_song_id": 900001, "lyrics_text": LYRICS}
        )

        assert response.status_code == 403
