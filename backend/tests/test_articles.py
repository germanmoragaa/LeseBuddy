import unicodedata

from factories import make_user
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

VALID_PASSWORD = "correct horse battery staple"


def _login_as(client: TestClient, db_session: Session, *, username: str, email: str) -> None:
    make_user(
        db_session, email=email, username=username, password=VALID_PASSWORD, email_verified=True
    )
    response = client.post(
        "/api/v1/auth/login", json={"identifier": username, "password": VALID_PASSWORD}
    )
    assert response.status_code == 200


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
            "title",
            "source_url",
            "language",
            "created_at",
            "updated_at",
            "word_count",
            "excerpt",
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
