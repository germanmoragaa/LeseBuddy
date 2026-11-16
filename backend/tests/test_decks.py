import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from factories import make_user
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_clock
from app.main import app as fastapi_app
from app.models import Deck, DeckItem, Flashcard
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


def _save_word(
    client: TestClient, article_id: str, word: str, deck_ids: list[str] | None = None
) -> dict:
    start, end = _token_span(client, article_id, word)
    payload = {"article_id": article_id, "start": start, "end": end}
    if deck_ids is not None:
        payload["deck_ids"] = deck_ids
    response = client.post("/api/v1/vocabulary", json=payload)
    assert response.status_code == 201
    return response.json()["item"]


def _create_deck(client: TestClient, name: str, description: str | None = None) -> dict:
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    response = client.post("/api/v1/decks", json=payload)
    assert response.status_code == 201
    return response.json()


class TestCreateDeck:
    def test_creates_deck_with_zero_counts(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")

        response = client.post(
            "/api/v1/decks", json={"name": "Food words", "description": "kitchen vocab"}
        )

        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Food words"
        assert body["description"] == "kitchen vocab"
        assert body["total_count"] == 0
        assert body["due_count"] == 0

    def test_description_is_optional(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")

        response = client.post("/api/v1/decks", json={"name": "Travel"})

        assert response.status_code == 201
        assert response.json()["description"] is None

    def test_rejects_empty_name(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")

        response = client.post("/api/v1/decks", json={"name": "   "})

        assert response.status_code == 422

    def test_duplicate_name_same_user_gets_409(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        _create_deck(client, "Food words")

        response = client.post("/api/v1/decks", json={"name": "food words"})

        assert response.status_code == 409
        assert response.json()["detail"][0]["loc"] == ["body", "name"]

    def test_same_name_different_users_both_succeed(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        _create_deck(client, "Food words")
        client.post("/api/v1/auth/logout")

        _login_as(client, db_session, username="bailey_jones", email="bailey@example.com")
        response = client.post("/api/v1/decks", json={"name": "Food words"})

        assert response.status_code == 201

    def test_unverified_user_gets_403(self, client: TestClient, db_session: Session) -> None:
        make_user(
            db_session, email="alex@example.com", username="alex_morgan", password=VALID_PASSWORD
        )
        client.post(
            "/api/v1/auth/login", json={"identifier": "alex_morgan", "password": VALID_PASSWORD}
        )

        response = client.post("/api/v1/decks", json={"name": "Food words"})

        assert response.status_code == 403


class TestListAndGetDeck:
    def test_lists_only_own_decks(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        _create_deck(client, "Food words")
        client.post("/api/v1/auth/logout")

        _login_as(client, db_session, username="bailey_jones", email="bailey@example.com")
        _create_deck(client, "Travel")

        response = client.get("/api/v1/decks")

        assert response.status_code == 200
        names = [item["name"] for item in response.json()["items"]]
        assert names == ["Travel"]

    def test_counts_total_and_due_cards(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        before_save = datetime.now(UTC)
        deck = _create_deck(client, "Food words")
        article_id = _create_article(client, "Der Hund schläft. Das Buch liegt da.")
        hund = _save_word(client, article_id, "Hund", deck_ids=[deck["id"]])
        _save_word(client, article_id, "Buch", deck_ids=[deck["id"]])

        response = client.get(f"/api/v1/decks/{deck['id']}")
        assert response.status_code == 200
        body = response.json()
        assert body["total_count"] == 2
        assert body["due_count"] == 2

        # Making one card not-yet-due must drop it from due_count but not total_count.
        card = db_session.query(Flashcard).filter_by(vocabulary_item_id=uuid.UUID(hund["id"])).one()
        card.due_at = before_save + timedelta(days=5)
        db_session.commit()

        response = client.get(f"/api/v1/decks/{deck['id']}")
        body = response.json()
        assert body["total_count"] == 2
        assert body["due_count"] == 1

    def test_list_counts_are_correct_per_deck_with_one_aggregated_query_no_n_plus_1(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        """Not a strict query-count assertion (that would overfit to the exact ORM calls) -
        this exercises the thing that would break if counting went back to one query per
        deck: two decks' counts must each reflect only their own items, computed in one
        request."""
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        deck_a = _create_deck(client, "Deck A")
        deck_b = _create_deck(client, "Deck B")
        article_id = _create_article(client, "Der Hund schläft. Das Buch liegt da.")
        _save_word(client, article_id, "Hund", deck_ids=[deck_a["id"]])
        _save_word(client, article_id, "Buch", deck_ids=[deck_b["id"]])

        response = client.get("/api/v1/decks")

        assert response.status_code == 200
        by_name = {item["name"]: item for item in response.json()["items"]}
        assert by_name["Deck A"]["total_count"] == 1
        assert by_name["Deck B"]["total_count"] == 1

    def test_get_other_users_deck_gets_404(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        deck = _create_deck(client, "Food words")
        client.post("/api/v1/auth/logout")

        _login_as(client, db_session, username="bailey_jones", email="bailey@example.com")
        response = client.get(f"/api/v1/decks/{deck['id']}")

        assert response.status_code == 404

    def test_unknown_deck_gets_404(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")

        response = client.get(f"/api/v1/decks/{uuid.uuid4()}")

        assert response.status_code == 404


class TestUpdateDeck:
    def test_renames_deck(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        deck = _create_deck(client, "Food words")

        response = client.patch(f"/api/v1/decks/{deck['id']}", json={"name": "Kitchen words"})

        assert response.status_code == 200
        assert response.json()["name"] == "Kitchen words"

    def test_updates_description_only(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        deck = _create_deck(client, "Food words")

        response = client.patch(
            f"/api/v1/decks/{deck['id']}", json={"description": "new description"}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "Food words"
        assert body["description"] == "new description"

    def test_rename_to_existing_name_gets_409(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        _create_deck(client, "Food words")
        deck_b = _create_deck(client, "Travel")

        response = client.patch(f"/api/v1/decks/{deck_b['id']}", json={"name": "food words"})

        assert response.status_code == 409

    def test_other_users_deck_gets_404(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        deck = _create_deck(client, "Food words")
        client.post("/api/v1/auth/logout")

        _login_as(client, db_session, username="bailey_jones", email="bailey@example.com")
        response = client.patch(f"/api/v1/decks/{deck['id']}", json={"name": "Hijacked"})

        assert response.status_code == 404


class TestDeleteDeck:
    def test_delete_removes_deck_and_memberships_but_keeps_words_and_cards(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        deck = _create_deck(client, "Food words")
        article_id = _create_article(client, "Der Hund schläft.")
        item = _save_word(client, article_id, "Hund", deck_ids=[deck["id"]])

        response = client.delete(f"/api/v1/decks/{deck['id']}")
        assert response.status_code == 204

        assert client.get(f"/api/v1/decks/{deck['id']}").status_code == 404
        assert db_session.query(Deck).count() == 0
        assert db_session.query(DeckItem).count() == 0
        # The word and its flashcard both survive the deck's deletion.
        get_response = client.get(f"/api/v1/vocabulary/{item['id']}")
        assert get_response.status_code == 200
        assert (
            db_session.query(Flashcard).filter_by(vocabulary_item_id=uuid.UUID(item["id"])).count()
            == 1
        )

    def test_other_users_deck_gets_404(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        deck = _create_deck(client, "Food words")
        client.post("/api/v1/auth/logout")

        _login_as(client, db_session, username="bailey_jones", email="bailey@example.com")
        response = client.delete(f"/api/v1/decks/{deck['id']}")

        assert response.status_code == 404


class TestDeckItems:
    def test_bulk_add_is_idempotent(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        deck = _create_deck(client, "Food words")
        article_id = _create_article(client, "Der Hund schläft. Das Buch liegt da.")
        hund = _save_word(client, article_id, "Hund")
        buch = _save_word(client, article_id, "Buch")

        first = client.post(
            f"/api/v1/decks/{deck['id']}/items",
            json={"vocabulary_item_ids": [hund["id"], buch["id"]]},
        )
        second = client.post(
            f"/api/v1/decks/{deck['id']}/items",
            json={"vocabulary_item_ids": [hund["id"], buch["id"]]},
        )

        assert first.status_code == second.status_code == 204
        assert db_session.query(DeckItem).filter_by(deck_id=uuid.UUID(deck["id"])).count() == 2

    def test_add_unowned_item_gets_404(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client, "Der Hund schläft.")
        hund = _save_word(client, article_id, "Hund")
        client.post("/api/v1/auth/logout")

        _login_as(client, db_session, username="bailey_jones", email="bailey@example.com")
        deck = _create_deck(client, "Food words")

        response = client.post(
            f"/api/v1/decks/{deck['id']}/items", json={"vocabulary_item_ids": [hund["id"]]}
        )

        assert response.status_code == 404

    def test_add_items_to_other_users_deck_gets_404(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        deck = _create_deck(client, "Food words")
        article_id = _create_article(client, "Der Hund schläft.")
        hund = _save_word(client, article_id, "Hund")
        client.post("/api/v1/auth/logout")

        _login_as(client, db_session, username="bailey_jones", email="bailey@example.com")
        response = client.post(
            f"/api/v1/decks/{deck['id']}/items", json={"vocabulary_item_ids": [hund["id"]]}
        )

        assert response.status_code == 404

    def test_remove_item_from_deck(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        deck = _create_deck(client, "Food words")
        article_id = _create_article(client, "Der Hund schläft.")
        hund = _save_word(client, article_id, "Hund", deck_ids=[deck["id"]])

        response = client.delete(f"/api/v1/decks/{deck['id']}/items/{hund['id']}")

        assert response.status_code == 204
        assert db_session.query(DeckItem).filter_by(deck_id=uuid.UUID(deck["id"])).count() == 0

    def test_remove_item_not_a_member_is_a_no_op(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        deck = _create_deck(client, "Food words")
        article_id = _create_article(client, "Der Hund schläft.")
        hund = _save_word(client, article_id, "Hund")

        response = client.delete(f"/api/v1/decks/{deck['id']}/items/{hund['id']}")

        assert response.status_code == 204


class TestVocabularySaveWithDecks:
    def test_save_with_deck_ids_adds_memberships(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        deck = _create_deck(client, "Food words")
        article_id = _create_article(client, "Der Hund schläft.")

        item = _save_word(client, article_id, "Hund", deck_ids=[deck["id"]])

        assert item["deck_ids"] == [deck["id"]]

    def test_save_with_deck_ids_also_works_when_item_already_existed(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        deck = _create_deck(client, "Food words")
        article_id = _create_article(client, "Der Hund schläft.")
        _save_word(client, article_id, "Hund")

        second_article_id = _create_article(client, "Ein Hund bellt.")
        item = _save_word(client, second_article_id, "Hund", deck_ids=[deck["id"]])

        assert item["deck_ids"] == [deck["id"]]

    def test_save_with_unowned_deck_id_silently_ignored(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client, "Der Hund schläft.")
        other_deck_id = str(uuid.uuid4())
        start, end = _token_span(client, article_id, "Hund")

        response = client.post(
            "/api/v1/vocabulary",
            json={
                "article_id": article_id,
                "start": start,
                "end": end,
                "deck_ids": [other_deck_id],
            },
        )

        assert response.status_code == 201
        assert response.json()["item"]["deck_ids"] == []


class TestVocabularyDeckFilter:
    def test_filters_vocabulary_list_by_deck(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        deck = _create_deck(client, "Food words")
        article_id = _create_article(client, "Der Hund schläft. Das Buch liegt da.")
        _save_word(client, article_id, "Hund", deck_ids=[deck["id"]])
        _save_word(client, article_id, "Buch")

        response = client.get("/api/v1/vocabulary", params={"deck_id": deck["id"]})

        assert response.status_code == 200
        assert [item["lemma"] for item in response.json()["items"]] == ["Hund"]

    def test_other_users_deck_id_filter_gets_404(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        deck = _create_deck(client, "Food words")
        client.post("/api/v1/auth/logout")

        _login_as(client, db_session, username="bailey_jones", email="bailey@example.com")
        response = client.get("/api/v1/vocabulary", params={"deck_id": deck["id"]})

        assert response.status_code == 404


class TestReviewsDeckFilter:
    def test_due_cards_filtered_by_deck(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        deck = _create_deck(client, "Food words")
        article_id = _create_article(client, "Der Hund schläft. Das Buch liegt da.")
        hund = _save_word(client, article_id, "Hund", deck_ids=[deck["id"]])
        _save_word(client, article_id, "Buch")

        response = client.get("/api/v1/reviews/due", params={"deck_id": deck["id"]})

        assert response.status_code == 200
        items = response.json()["items"]
        assert [item["vocabulary_item_id"] for item in items] == [hund["id"]]

    def test_due_cards_unfiltered_is_unchanged(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        deck = _create_deck(client, "Food words")
        article_id = _create_article(client, "Der Hund schläft. Das Buch liegt da.")
        _save_word(client, article_id, "Hund", deck_ids=[deck["id"]])
        _save_word(client, article_id, "Buch")

        response = client.get("/api/v1/reviews/due")

        assert response.status_code == 200
        assert len(response.json()["items"]) == 2

    def test_summary_filtered_by_deck(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        deck = _create_deck(client, "Food words")
        article_id = _create_article(client, "Der Hund schläft. Das Buch liegt da.")
        _save_word(client, article_id, "Hund", deck_ids=[deck["id"]])
        _save_word(client, article_id, "Buch")

        response = client.get("/api/v1/reviews/summary", params={"deck_id": deck["id"]})

        assert response.status_code == 200
        body = response.json()
        assert body["total_cards"] == 1
        assert body["due_count"] == 1

    def test_summary_unfiltered_is_unchanged(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        deck = _create_deck(client, "Food words")
        article_id = _create_article(client, "Der Hund schläft. Das Buch liegt da.")
        _save_word(client, article_id, "Hund", deck_ids=[deck["id"]])
        _save_word(client, article_id, "Buch")

        response = client.get("/api/v1/reviews/summary")

        assert response.status_code == 200
        body = response.json()
        assert body["total_cards"] == 2
        assert body["due_count"] == 2

    def test_due_cards_other_users_deck_id_gets_404(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        deck = _create_deck(client, "Food words")
        client.post("/api/v1/auth/logout")

        _login_as(client, db_session, username="bailey_jones", email="bailey@example.com")
        response = client.get("/api/v1/reviews/due", params={"deck_id": deck["id"]})

        assert response.status_code == 404

    def test_summary_other_users_deck_id_gets_404(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        deck = _create_deck(client, "Food words")
        client.post("/api/v1/auth/logout")

        _login_as(client, db_session, username="bailey_jones", email="bailey@example.com")
        response = client.get("/api/v1/reviews/summary", params={"deck_id": deck["id"]})

        assert response.status_code == 404
