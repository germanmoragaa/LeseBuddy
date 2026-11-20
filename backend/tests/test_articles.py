import unicodedata
from collections.abc import Iterator
from contextlib import contextmanager

from factories import make_song, make_user
from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models import User

VALID_PASSWORD = "correct horse battery staple"


def _login_as(client: TestClient, db_session: Session, *, username: str, email: str) -> User:
    user = make_user(
        db_session, email=email, username=username, password=VALID_PASSWORD, email_verified=True
    )
    response = client.post(
        "/api/v1/auth/login", json={"identifier": username, "password": VALID_PASSWORD}
    )
    assert response.status_code == 200
    return user


class TestCreateArticle:
    def test_creates_and_returns_article(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")

        response = client.post(
            "/api/v1/articles",
            json={"title": "Der Froschkönig", "original_text": "Es war einmal..."},
        )

        assert response.status_code == 201
        body = response.json()
        assert body["title"] == "Der Froschkönig"
        assert body["original_text"] == "Es war einmal..."
        assert body["language"] == "de"

    def test_normalizes_text_to_nfc(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        # "ü" as a decomposed base letter + combining diaeresis (NFD), not the precomposed
        # NFC codepoint — must be stored normalized so later offset-based analysis is
        # consistent regardless of how the client encoded the input.
        decomposed = unicodedata.normalize("NFD", "Müller")
        assert decomposed != "Müller"

        response = client.post("/api/v1/articles", json={"original_text": decomposed})

        assert response.status_code == 201
        stored = response.json()["original_text"]
        assert stored == unicodedata.normalize("NFC", decomposed)
        assert stored == "Müller"

    def test_rejects_text_over_max_length(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")

        response = client.post("/api/v1/articles", json={"original_text": "a" * 50_001})

        assert response.status_code == 422

    def test_rejects_empty_text(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")

        response = client.post("/api/v1/articles", json={"original_text": ""})

        assert response.status_code == 422

    def test_unverified_user_gets_403(self, client: TestClient, db_session: Session) -> None:
        make_user(
            db_session, email="alex@example.com", username="alex_morgan", password=VALID_PASSWORD
        )
        client.post(
            "/api/v1/auth/login",
            json={"identifier": "alex_morgan", "password": VALID_PASSWORD},
        )

        response = client.post("/api/v1/articles", json={"original_text": "Hallo."})

        assert response.status_code == 403


class TestListArticles:
    def test_lists_only_own_articles_without_full_text(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        client.post("/api/v1/articles", json={"title": "First", "original_text": "Text eins."})
        client.post("/api/v1/articles", json={"title": "Second", "original_text": "Text zwei."})

        response = client.get("/api/v1/articles")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2
        assert body["page"] == 1
        assert body["page_size"] == 20
        items = body["items"]
        assert len(items) == 2
        assert {item["title"] for item in items} == {"First", "Second"}
        assert all("original_text" not in item for item in items)

    def test_response_has_exactly_the_paginated_shape_through_the_real_app(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        client.post("/api/v1/articles", json={"title": "First", "original_text": "Text eins."})

        response = client.get("/api/v1/articles")

        body = response.json()
        assert set(body.keys()) == {"items", "total", "page", "page_size"}
        assert set(body["items"][0].keys()) == {
            "id",
            "kind",
            "title",
            "source_url",
            "language",
            "created_at",
            "updated_at",
            "word_count",
            "excerpt",
            "last_opened_at",
            "progress_percent",
            "song",
        }

    def test_does_not_list_other_users_articles(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        client.post("/api/v1/articles", json={"original_text": "Alex's text."})
        client.post("/api/v1/auth/logout")

        _login_as(client, db_session, username="bailey_jones", email="bailey@example.com")
        response = client.get("/api/v1/articles")

        assert response.status_code == 200
        assert response.json() == {"items": [], "total": 0, "page": 1, "page_size": 20}

    def test_orders_most_recently_created_first(
        self, client: TestClient, db_session: Session
    ) -> None:
        # The whole test runs inside one DB transaction (see conftest.db_session), so Postgres'
        # now() ties across both inserts — backdate the first article explicitly to exercise the
        # ORDER BY clause itself rather than relying on wall-clock gaps between requests.
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        first = client.post(
            "/api/v1/articles", json={"title": "First", "original_text": "Text eins."}
        ).json()
        client.post("/api/v1/articles", json={"title": "Second", "original_text": "Text zwei."})
        db_session.execute(
            text("UPDATE articles SET created_at = created_at - interval '1 hour' WHERE id = :id"),
            {"id": first["id"]},
        )
        db_session.commit()

        response = client.get("/api/v1/articles")

        titles = [item["title"] for item in response.json()["items"]]
        assert titles == ["Second", "First"]

    def test_includes_word_count_and_excerpt(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        client.post(
            "/api/v1/articles", json={"title": "First", "original_text": "Ein kurzer Text hier."}
        )

        item = client.get("/api/v1/articles").json()["items"][0]

        assert item["word_count"] == 4
        assert item["excerpt"] == "Ein kurzer Text hier."

    def test_paginates_results(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        for index in range(3):
            client.post(
                "/api/v1/articles", json={"title": f"Text {index}", "original_text": "Hallo."}
            )

        response = client.get("/api/v1/articles", params={"page": 1, "page_size": 2})

        body = response.json()
        assert body["total"] == 3
        assert len(body["items"]) == 2

        second_page = client.get("/api/v1/articles", params={"page": 2, "page_size": 2}).json()
        assert len(second_page["items"]) == 1

    def test_default_sort_ignores_last_opened_at(
        self, client: TestClient, db_session: Session
    ) -> None:
        # Without sort=recent, ordering must stay creation-order even once an article has
        # been opened — opening an old article shouldn't reorder the default article list.
        # As in test_orders_most_recently_created_first above, the whole test runs inside one
        # DB transaction, so Postgres' now() ties across both inserts — backdate the first
        # article explicitly rather than relying on wall-clock gaps between requests.
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        first = client.post(
            "/api/v1/articles", json={"title": "First", "original_text": "Text eins."}
        ).json()
        client.post("/api/v1/articles", json={"title": "Second", "original_text": "Text zwei."})
        db_session.execute(
            text("UPDATE articles SET created_at = created_at - interval '1 hour' WHERE id = :id"),
            {"id": first["id"]},
        )
        db_session.commit()
        client.post(f"/api/v1/articles/{first['id']}/open")

        response = client.get("/api/v1/articles")

        titles = [item["title"] for item in response.json()["items"]]
        assert titles == ["Second", "First"]

    def test_sort_recent_orders_by_last_opened_then_created(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        first = client.post(
            "/api/v1/articles", json={"title": "First", "original_text": "Text eins."}
        ).json()
        client.post("/api/v1/articles", json={"title": "Second", "original_text": "Text zwei."})

        # Opening the older article should bump it to the top under sort=recent.
        open_response = client.post(f"/api/v1/articles/{first['id']}/open")
        assert open_response.status_code == 200

        response = client.get("/api/v1/articles", params={"sort": "recent"})

        titles = [item["title"] for item in response.json()["items"]]
        assert titles == ["First", "Second"]

    def test_sort_recent_falls_back_to_created_at_when_never_opened(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        first = client.post(
            "/api/v1/articles", json={"title": "First", "original_text": "Text eins."}
        ).json()
        client.post("/api/v1/articles", json={"title": "Second", "original_text": "Text zwei."})
        db_session.execute(
            text("UPDATE articles SET created_at = created_at - interval '1 hour' WHERE id = :id"),
            {"id": first["id"]},
        )
        db_session.commit()

        response = client.get("/api/v1/articles", params={"sort": "recent"})

        titles = [item["title"] for item in response.json()["items"]]
        assert titles == ["Second", "First"]

    def test_progress_percent_is_null_until_a_position_is_saved(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        client.post("/api/v1/articles", json={"original_text": "Ein kurzer Text."})

        item = client.get("/api/v1/articles").json()["items"][0]

        assert item["last_opened_at"] is None
        assert item["progress_percent"] is None

    def test_progress_percent_reflects_saved_reading_position(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        # "Ein kurzer Text." has 16 code points; offset 8 is the halfway point.
        created = client.post("/api/v1/articles", json={"original_text": "Ein kurzer Text."}).json()
        client.patch(f"/api/v1/articles/{created['id']}/position", json={"offset": 8})

        item = client.get("/api/v1/articles").json()["items"][0]

        assert item["progress_percent"] == 50.0


class TestGetArticle:
    def test_owner_can_fetch_their_article(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        created = client.post(
            "/api/v1/articles", json={"title": "Mine", "original_text": "Mein Text."}
        ).json()

        response = client.get(f"/api/v1/articles/{created['id']}")

        assert response.status_code == 200
        assert response.json()["original_text"] == "Mein Text."

    def test_other_user_gets_404_not_403(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        created = client.post(
            "/api/v1/articles", json={"original_text": "Alex's private text."}
        ).json()
        client.post("/api/v1/auth/logout")

        _login_as(client, db_session, username="bailey_jones", email="bailey@example.com")
        response = client.get(f"/api/v1/articles/{created['id']}")

        assert response.status_code == 404

    def test_unknown_id_gets_404(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")

        response = client.get("/api/v1/articles/00000000-0000-0000-0000-000000000000")

        assert response.status_code == 404


class TestUpdateArticle:
    def test_owner_can_rename_their_article(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        created = client.post(
            "/api/v1/articles", json={"title": "Old title", "original_text": "Mein Text."}
        ).json()

        response = client.patch(f"/api/v1/articles/{created['id']}", json={"title": "New title"})

        assert response.status_code == 200
        assert response.json()["title"] == "New title"
        assert client.get(f"/api/v1/articles/{created['id']}").json()["title"] == "New title"

    def test_rejects_empty_title(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        created = client.post(
            "/api/v1/articles", json={"title": "Old title", "original_text": "Mein Text."}
        ).json()

        response = client.patch(f"/api/v1/articles/{created['id']}", json={"title": ""})

        assert response.status_code == 422

    def test_other_user_gets_404_not_403(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        created = client.post(
            "/api/v1/articles", json={"original_text": "Alex's private text."}
        ).json()
        client.post("/api/v1/auth/logout")

        _login_as(client, db_session, username="bailey_jones", email="bailey@example.com")
        response = client.patch(f"/api/v1/articles/{created['id']}", json={"title": "Hijacked"})

        assert response.status_code == 404


class TestDeleteArticle:
    def test_owner_can_delete_their_article(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        created = client.post("/api/v1/articles", json={"original_text": "Mein Text."}).json()

        response = client.delete(f"/api/v1/articles/{created['id']}")

        assert response.status_code == 204
        assert client.get(f"/api/v1/articles/{created['id']}").status_code == 404

    def test_other_user_gets_404_not_403(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        created = client.post(
            "/api/v1/articles", json={"original_text": "Alex's private text."}
        ).json()
        client.post("/api/v1/auth/logout")

        _login_as(client, db_session, username="bailey_jones", email="bailey@example.com")
        response = client.delete(f"/api/v1/articles/{created['id']}")

        assert response.status_code == 404


class TestOpenArticle:
    def test_sets_last_opened_at(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        created = client.post("/api/v1/articles", json={"original_text": "Mein Text."}).json()
        assert created["last_opened_at"] is None

        response = client.post(f"/api/v1/articles/{created['id']}/open")

        assert response.status_code == 200
        assert response.json()["last_opened_at"] is not None

    def test_does_not_set_last_opened_at_on_get(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        created = client.post("/api/v1/articles", json={"original_text": "Mein Text."}).json()

        client.get(f"/api/v1/articles/{created['id']}")

        assert client.get(f"/api/v1/articles/{created['id']}").json()["last_opened_at"] is None

    def test_other_user_gets_404_not_403(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        created = client.post(
            "/api/v1/articles", json={"original_text": "Alex's private text."}
        ).json()
        client.post("/api/v1/auth/logout")

        _login_as(client, db_session, username="bailey_jones", email="bailey@example.com")
        response = client.post(f"/api/v1/articles/{created['id']}/open")

        assert response.status_code == 404

    def test_unknown_id_gets_404(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")

        response = client.post("/api/v1/articles/00000000-0000-0000-0000-000000000000/open")

        assert response.status_code == 404


class TestUpdateReadingPosition:
    def test_owner_can_save_a_valid_position(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        created = client.post("/api/v1/articles", json={"original_text": "Ein kurzer Text."}).json()

        response = client.patch(f"/api/v1/articles/{created['id']}/position", json={"offset": 8})

        assert response.status_code == 200
        assert response.json()["reading_position"] == 8

    def test_rejects_negative_offset(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        created = client.post("/api/v1/articles", json={"original_text": "Ein kurzer Text."}).json()

        response = client.patch(f"/api/v1/articles/{created['id']}/position", json={"offset": -1})

        assert response.status_code == 422

    def test_rejects_offset_past_the_end_of_the_text(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        created = client.post("/api/v1/articles", json={"original_text": "Ein kurzer Text."}).json()

        response = client.patch(f"/api/v1/articles/{created['id']}/position", json={"offset": 999})

        assert response.status_code == 422

    def test_accepts_offset_equal_to_text_length(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        created = client.post("/api/v1/articles", json={"original_text": "Ein kurzer Text."}).json()

        response = client.patch(f"/api/v1/articles/{created['id']}/position", json={"offset": 16})

        assert response.status_code == 200
        assert response.json()["reading_position"] == 16

    def test_other_user_gets_404_not_403(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        created = client.post(
            "/api/v1/articles", json={"original_text": "Alex's private text."}
        ).json()
        client.post("/api/v1/auth/logout")

        _login_as(client, db_session, username="bailey_jones", email="bailey@example.com")
        response = client.patch(f"/api/v1/articles/{created['id']}/position", json={"offset": 1})

        assert response.status_code == 404


@contextmanager
def _count_queries(engine: Engine) -> Iterator[list[str]]:
    statements: list[str] = []

    def record(conn, cursor, statement, parameters, context, executemany) -> None:  # noqa: ANN001
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", record)


EXPECTED_SONG_METADATA = {
    "title": "Nachtlicht",
    "primary_artist": "Die Erfundenen",
    "album": "Lieder aus Papier",
    "release_date": "2021-05-14",
    "release_date_display": "May 14, 2021",
    "cover_url": "https://images.genius.com/example-cover.jpg",
    "cover_thumbnail_url": "https://images.genius.com/example-cover-300x300.jpg",
    "genius_url": "https://genius.com/Die-erfundenen-nachtlicht-lyrics",
}


class TestSongMetadataInResponses:
    def test_text_article_detail_has_kind_text_and_null_song(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        created = client.post("/api/v1/articles", json={"original_text": "Mein Text."}).json()

        assert created["kind"] == "text"
        assert created["song"] is None
        body = client.get(f"/api/v1/articles/{created['id']}").json()
        assert body["kind"] == "text"
        assert body["song"] is None

    def test_text_article_list_item_has_kind_text_and_null_song(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        client.post("/api/v1/articles", json={"original_text": "Mein Text."})

        item = client.get("/api/v1/articles").json()["items"][0]

        assert item["kind"] == "text"
        assert item["song"] is None

    def test_song_article_detail_includes_full_metadata(
        self, client: TestClient, db_session: Session
    ) -> None:
        user = _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article = make_song(db_session, user)
        db_session.expire_all()

        body = client.get(f"/api/v1/articles/{article.id}").json()

        assert body["kind"] == "song"
        assert body["song"] == EXPECTED_SONG_METADATA
        assert body["original_text"] == article.original_text

    def test_song_article_list_item_includes_full_metadata(
        self, client: TestClient, db_session: Session
    ) -> None:
        user = _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        make_song(db_session, user)
        client.post("/api/v1/articles", json={"title": "Plain", "original_text": "Text."})
        db_session.expire_all()

        items = client.get("/api/v1/articles").json()["items"]

        by_kind = {item["kind"]: item for item in items}
        assert by_kind["song"]["song"] == EXPECTED_SONG_METADATA
        assert by_kind["text"]["song"] is None

    def test_song_metadata_omits_internal_fields(
        self, client: TestClient, db_session: Session
    ) -> None:
        user = _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article = make_song(db_session, user)

        song = client.get(f"/api/v1/articles/{article.id}").json()["song"]

        assert "genius_song_id" not in song
        assert "metadata_fetched_at" not in song

    def test_song_without_genius_metadata_returns_nulls(
        self, client: TestClient, db_session: Session
    ) -> None:
        user = _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article = make_song(
            db_session,
            user,
            genius_song_id=None,
            album=None,
            release_date=None,
            release_date_display=None,
            cover_url=None,
            cover_thumbnail_url=None,
            genius_url=None,
        )

        song = client.get(f"/api/v1/articles/{article.id}").json()["song"]

        assert song == {
            "title": "Nachtlicht",
            "primary_artist": "Die Erfundenen",
            "album": None,
            "release_date": None,
            "release_date_display": None,
            "cover_url": None,
            "cover_thumbnail_url": None,
            "genius_url": None,
        }

    def test_list_query_count_does_not_grow_with_number_of_songs(
        self, client: TestClient, db_session: Session, test_engine: Engine
    ) -> None:
        user = _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        make_song(db_session, user, genius_song_id=1)
        # Expired, like a fresh request: a lazy-loaded Article.song would hit the database
        # once per row instead of finding the songs already in the identity map.
        db_session.expire_all()
        with _count_queries(test_engine) as with_one_song:
            assert len(client.get("/api/v1/articles").json()["items"]) == 1

        for genius_song_id in range(2, 7):
            make_song(db_session, user, genius_song_id=genius_song_id)
        db_session.expire_all()
        with _count_queries(test_engine) as with_six_songs:
            items = client.get("/api/v1/articles").json()["items"]

        assert len(items) == 6
        assert all(item["song"] is not None for item in items)
        assert len(with_six_songs) == len(with_one_song)
        song_selects = [s for s in with_six_songs if "FROM songs" in s or "JOIN songs" in s]
        assert len(song_selects) == 1
