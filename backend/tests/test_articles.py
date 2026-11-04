import unicodedata

from factories import make_user
from fastapi.testclient import TestClient
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
        assert len(body) == 2
        assert {item["title"] for item in body} == {"First", "Second"}
        assert all("original_text" not in item for item in body)

    def test_does_not_list_other_users_articles(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        client.post("/api/v1/articles", json={"original_text": "Alex's text."})
        client.post("/api/v1/auth/logout")

        _login_as(client, db_session, username="bailey_jones", email="bailey@example.com")
        response = client.get("/api/v1/articles")

        assert response.status_code == 200
        assert response.json() == []


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
