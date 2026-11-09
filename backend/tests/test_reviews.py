import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from factories import make_user
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_clock
from app.main import app as fastapi_app
from app.models import Flashcard, ReviewLog
from app.scripts.import_dictionary import import_dictionary

FIXTURE_PATH = str(Path(__file__).parent / "fixtures" / "dictionary" / "sample.jsonl")
VALID_PASSWORD = "correct horse battery staple"


@pytest.fixture
def dictionary(db_session: Session) -> None:
    import_dictionary(FIXTURE_PATH, "test-version", db=db_session)


@pytest.fixture(autouse=True)
def _clear_clock_override():
    yield
    fastapi_app.dependency_overrides.pop(get_clock, None)


def _freeze_clock(now: datetime) -> None:
    fastapi_app.dependency_overrides[get_clock] = lambda: lambda: now


def _login_as(client: TestClient, db_session: Session, *, username: str, email: str) -> None:
    make_user(
        db_session, email=email, username=username, password=VALID_PASSWORD, email_verified=True
    )
    response = client.post(
        "/api/v1/auth/login", json={"identifier": username, "password": VALID_PASSWORD}
    )
    assert response.status_code == 200


def _create_article(client: TestClient, text: str) -> str:
    response = client.post("/api/v1/articles", json={"original_text": text})
    assert response.status_code == 201
    return response.json()["id"]


def _token_span(client: TestClient, article_id: str, text: str) -> tuple[int, int]:
    analysis = client.get(f"/api/v1/articles/{article_id}/analysis").json()
    for token in analysis["tokens"]:
        if token["text"] == text:
            return token["start"], token["end"]
    raise AssertionError(f"no token with text {text!r} in analysis")


def _save_word(client: TestClient, article_id: str, word: str) -> dict:
    start, end = _token_span(client, article_id, word)
    response = client.post(
        "/api/v1/vocabulary", json={"article_id": article_id, "start": start, "end": end}
    )
    assert response.status_code == 201
    return response.json()["item"]


class TestDueCards:
    def test_lists_due_cards_ordered_by_due_at(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client, "Der Hund schläft. Das Buch liegt da.")
        buch = _save_word(client, article_id, "Buch")
        hund = _save_word(client, article_id, "Hund")

        response = client.get("/api/v1/reviews/due")

        assert response.status_code == 200
        items = response.json()["items"]
        assert [item["vocabulary_item_id"] for item in items] == [buch["id"], hund["id"]]

    def test_due_card_front_and_back_content(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client, "Der Hund schläft.")
        _save_word(client, article_id, "Hund")

        response = client.get("/api/v1/reviews/due")

        item = response.json()["items"][0]
        assert item["front"]["display_form"] == "Hund"
        assert item["front"]["part_of_speech"] == "NOUN"
        assert item["front"]["gender"] == "Masc"
        # No /translate call was ever made, so there's nothing in translation_cache yet —
        # lookup_cached_translation is cache-only and never calls the provider itself.
        assert item["back"]["translation"] is None
        assert item["back"]["glosses"] == ["dog"]
        assert item["back"]["context_sentence"] == "Der Hund schläft."
        assert set(item["preview"].keys()) == {"again", "hard", "good", "easy"}

    def test_excludes_cards_not_yet_due(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        before_save = datetime.now(UTC)
        article_id = _create_article(client, "Der Hund schläft.")
        _save_word(client, article_id, "Hund")

        _freeze_clock(before_save - timedelta(hours=1))
        response = client.get("/api/v1/reviews/due")

        assert response.json()["items"] == []

    def test_includes_cards_once_due(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        before_save = datetime.now(UTC)
        article_id = _create_article(client, "Der Hund schläft.")
        _save_word(client, article_id, "Hund")

        _freeze_clock(before_save + timedelta(hours=1))
        response = client.get("/api/v1/reviews/due")

        assert len(response.json()["items"]) == 1

    def test_respects_limit(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(
            client, "Ich rufe dich morgen an. Der Hund schläft. Das Buch liegt da."
        )
        _save_word(client, article_id, "rufe")
        _save_word(client, article_id, "Hund")
        _save_word(client, article_id, "Buch")

        response = client.get("/api/v1/reviews/due", params={"limit": 2})

        assert len(response.json()["items"]) == 2

    def test_unverified_user_gets_403(self, client: TestClient, db_session: Session) -> None:
        make_user(
            db_session, email="alex@example.com", username="alex_morgan", password=VALID_PASSWORD
        )
        client.post(
            "/api/v1/auth/login", json={"identifier": "alex_morgan", "password": VALID_PASSWORD}
        )

        response = client.get("/api/v1/reviews/due")

        assert response.status_code == 403


class TestReviewSummary:
    def test_counts_due_and_total_cards(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        before_save = datetime.now(UTC)
        article_id = _create_article(client, "Der Hund schläft. Das Buch liegt da.")
        _save_word(client, article_id, "Hund")
        _save_word(client, article_id, "Buch")

        response = client.get("/api/v1/reviews/summary")

        assert response.status_code == 200
        body = response.json()
        assert body["total_cards"] == 2
        assert body["due_count"] == 2
        assert body["next_due_at"] is not None
        assert datetime.fromisoformat(body["next_due_at"]) >= before_save

    def test_due_count_excludes_not_yet_due_cards(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        before_save = datetime.now(UTC)
        article_id = _create_article(client, "Der Hund schläft.")
        _save_word(client, article_id, "Hund")

        _freeze_clock(before_save - timedelta(hours=1))
        response = client.get("/api/v1/reviews/summary")

        body = response.json()
        assert body["total_cards"] == 1
        assert body["due_count"] == 0

    def test_zero_cards(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")

        response = client.get("/api/v1/reviews/summary")

        body = response.json()
        assert body == {"due_count": 0, "next_due_at": None, "total_cards": 0}


class TestSubmitReview:
    def _flashcard_id_for(self, db_session: Session, vocabulary_item_id: str) -> str:
        card = (
            db_session.query(Flashcard)
            .filter_by(vocabulary_item_id=uuid.UUID(vocabulary_item_id))
            .one()
        )
        return str(card.id)

    def test_updates_card_and_inserts_exactly_one_log(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client, "Der Hund schläft.")
        item = _save_word(client, article_id, "Hund")
        flashcard_id = self._flashcard_id_for(db_session, item["id"])
        now = datetime(2026, 2, 1, tzinfo=UTC)
        _freeze_clock(now)

        response = client.post(
            "/api/v1/reviews", json={"flashcard_id": flashcard_id, "rating": "good"}
        )

        assert response.status_code == 201
        body = response.json()
        assert body["flashcard_id"] == flashcard_id
        assert body["rating"] == "good"
        assert body["interval_days"] == 1
        assert datetime.fromisoformat(body["reviewed_at"]) == now

        db_session.expire_all()
        card = db_session.get(Flashcard, uuid.UUID(flashcard_id))
        assert card.repetitions == 1
        assert card.interval_days == 1
        assert card.last_reviewed_at == now
        assert db_session.query(ReviewLog).filter_by(flashcard_id=card.id).count() == 1

    def test_idempotent_on_client_review_id(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client, "Der Hund schläft.")
        item = _save_word(client, article_id, "Hund")
        flashcard_id = self._flashcard_id_for(db_session, item["id"])
        client_review_id = str(uuid.uuid4())

        first = client.post(
            "/api/v1/reviews",
            json={
                "flashcard_id": flashcard_id,
                "rating": "good",
                "client_review_id": client_review_id,
            },
        )
        second = client.post(
            "/api/v1/reviews",
            json={
                "flashcard_id": flashcard_id,
                "rating": "easy",
                "client_review_id": client_review_id,
            },
        )

        assert first.status_code == second.status_code == 201
        assert first.json() == second.json()
        db_session.expire_all()
        assert db_session.query(ReviewLog).count() == 1
        card = db_session.query(Flashcard).filter_by(id=uuid.UUID(flashcard_id)).one()
        assert card.repetitions == 1  # the second ("easy") submission was never applied

    def test_unknown_flashcard_gets_404(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")

        response = client.post(
            "/api/v1/reviews",
            json={"flashcard_id": "00000000-0000-0000-0000-000000000000", "rating": "good"},
        )

        assert response.status_code == 404

    def test_other_users_flashcard_gets_404(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client, "Der Hund schläft.")
        item = _save_word(client, article_id, "Hund")
        flashcard_id = self._flashcard_id_for(db_session, item["id"])
        client.post("/api/v1/auth/logout")

        _login_as(client, db_session, username="bailey_jones", email="bailey@example.com")
        response = client.post(
            "/api/v1/reviews", json={"flashcard_id": flashcard_id, "rating": "good"}
        )

        assert response.status_code == 404

    def test_unverified_user_gets_403(self, client: TestClient, db_session: Session) -> None:
        make_user(
            db_session, email="alex@example.com", username="alex_morgan", password=VALID_PASSWORD
        )
        client.post(
            "/api/v1/auth/login", json={"identifier": "alex_morgan", "password": VALID_PASSWORD}
        )

        response = client.post(
            "/api/v1/reviews",
            json={"flashcard_id": "00000000-0000-0000-0000-000000000000", "rating": "good"},
        )

        assert response.status_code == 403


class TestVocabularyIntegration:
    def test_saving_vocabulary_creates_a_due_card(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        before = datetime.now(UTC)
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client, "Der Hund schläft.")
        item = _save_word(client, article_id, "Hund")

        card = db_session.query(Flashcard).filter_by(vocabulary_item_id=uuid.UUID(item["id"])).one()
        assert card.ease_factor == pytest.approx(2.5)
        assert card.interval_days == 0
        assert card.repetitions == 0
        assert card.due_at >= before

    def test_deleting_a_vocabulary_item_cascades_its_card_but_keeps_review_logs(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client, "Der Hund schläft.")
        item = _save_word(client, article_id, "Hund")
        flashcard_id = (
            db_session.query(Flashcard).filter_by(vocabulary_item_id=uuid.UUID(item["id"])).one().id
        )
        client.post("/api/v1/reviews", json={"flashcard_id": str(flashcard_id), "rating": "good"})

        delete_response = client.delete(f"/api/v1/vocabulary/{item['id']}")
        assert delete_response.status_code == 204

        db_session.expire_all()
        assert db_session.query(Flashcard).filter_by(id=flashcard_id).first() is None
        log = db_session.query(ReviewLog).filter_by(lemma="Hund").one()
        assert log.flashcard_id is None
