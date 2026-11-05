from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from factories import make_user
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import ArticleVocabulary, VocabularyItem
from app.scripts.import_dictionary import import_dictionary
from app.services import vocabulary_service

FIXTURE_PATH = str(Path(__file__).parent / "fixtures" / "dictionary" / "sample.jsonl")
VALID_PASSWORD = "correct horse battery staple"


@pytest.fixture
def dictionary(db_session: Session) -> None:
    import_dictionary(FIXTURE_PATH, "test-version", db=db_session)


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


def _save(client: TestClient, article_id: str, start: int, end: int):
    return client.post(
        "/api/v1/vocabulary", json={"article_id": article_id, "start": start, "end": end}
    )


class TestSaveVocabulary:
    def test_creates_item_and_occurrence_with_dictionary_data(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client, "Der Hund schläft.")
        start, end = _token_span(client, article_id, "Hund")

        response = _save(client, article_id, start, end)

        assert response.status_code == 201
        body = response.json()
        assert body["already_saved"] is False
        item = body["item"]
        assert item["lemma"] == "Hund"
        assert item["display_form"] == "Hund"
        assert item["grammar_metadata"]["gender"] == "Masc"
        assert item["grammar_metadata"]["plural"] == "Hunde"
        assert item["meaning"] == "dog"

    def test_saving_same_occurrence_again_is_not_duplicated(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client, "Der Hund schläft.")
        start, end = _token_span(client, article_id, "Hund")

        first = _save(client, article_id, start, end)
        second = _save(client, article_id, start, end)

        assert first.status_code == second.status_code == 201
        assert first.json()["already_saved"] is False
        assert second.json()["already_saved"] is True
        assert first.json()["item"]["id"] == second.json()["item"]["id"]
        assert db_session.query(ArticleVocabulary).count() == 1
        assert db_session.query(VocabularyItem).count() == 1

    def test_saving_same_lemma_in_a_different_article_reuses_item_new_occurrence(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_1 = _create_article(client, "Der Hund schläft.")
        start_1, end_1 = _token_span(client, article_1, "Hund")
        article_2 = _create_article(client, "Ein Hund bellt.")
        start_2, end_2 = _token_span(client, article_2, "Hund")

        first = _save(client, article_1, start_1, end_1)
        second = _save(client, article_2, start_2, end_2)

        assert first.json()["item"]["id"] == second.json()["item"]["id"]
        assert second.json()["already_saved"] is False
        assert db_session.query(VocabularyItem).count() == 1
        assert db_session.query(ArticleVocabulary).count() == 2

    def test_concurrent_save_race_reuses_item_not_integrity_error(
        self, client: TestClient, db_session: Session, dictionary: None, monkeypatch
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client, "Der Hund schläft.")
        start, end = _token_span(client, article_id, "Hund")

        real_find = vocabulary_service._find_item_by_lemma
        calls = {"n": 0}

        def flaky_find(db, user_id, lemma):
            calls["n"] += 1
            if calls["n"] == 1:
                return None
            return real_find(db, user_id, lemma)

        monkeypatch.setattr(vocabulary_service, "_find_item_by_lemma", flaky_find)

        response = _save(client, article_id, start, end)

        assert response.status_code == 201
        assert db_session.query(VocabularyItem).count() == 1

    def test_phrase_and_separable_verb_save_correctly(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client, "Ich rufe dich morgen an. Vor allem mag ich das.")

        verb_start, verb_end = _token_span(client, article_id, "rufe")
        verb_response = _save(client, article_id, verb_start, verb_end)
        assert verb_response.status_code == 201
        assert verb_response.json()["item"]["lemma"] == "anrufen"

        vor_start, _ = _token_span(client, article_id, "Vor")
        _, allem_end = _token_span(client, article_id, "allem")
        phrase_response = _save(client, article_id, vor_start, allem_end)
        assert phrase_response.status_code == 201
        assert phrase_response.json()["item"]["lemma"] == "Vor allem"

    def test_other_user_article_gets_404(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client, "Der Hund schläft.")
        client.post("/api/v1/auth/logout")

        _login_as(client, db_session, username="bailey_jones", email="bailey@example.com")
        response = _save(client, article_id, 0, 3)

        assert response.status_code == 404

    def test_unverified_user_gets_403(self, client: TestClient, db_session: Session) -> None:
        make_user(
            db_session, email="alex@example.com", username="alex_morgan", password=VALID_PASSWORD
        )
        client.post(
            "/api/v1/auth/login",
            json={"identifier": "alex_morgan", "password": VALID_PASSWORD},
        )

        response = _save(client, "00000000-0000-0000-0000-000000000000", 0, 3)

        assert response.status_code == 403


class TestListVocabulary:
    def test_lists_newest_first(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client, "Der Hund schläft. Das Buch liegt da.")
        hund_start, hund_end = _token_span(client, article_id, "Hund")
        buch_start, buch_end = _token_span(client, article_id, "Buch")
        _save(client, article_id, hund_start, hund_end)
        _save(client, article_id, buch_start, buch_end)
        # Both saves happen inside this test's single savepoint-joined transaction, where
        # Postgres's now() is transaction-scoped — back-to-back inserts can get an identical
        # created_at. Force an unambiguous order rather than relying on real-time ticking.
        db_session.query(VocabularyItem).filter_by(lemma="Buch").update(
            {"created_at": datetime.now(UTC) + timedelta(seconds=1)}
        )
        db_session.commit()

        response = client.get("/api/v1/vocabulary")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2
        assert [item["lemma"] for item in body["items"]] == ["Buch", "Hund"]

    def test_search_filters_by_text(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client, "Der Hund schläft. Das Buch liegt da.")
        hund_start, hund_end = _token_span(client, article_id, "Hund")
        buch_start, buch_end = _token_span(client, article_id, "Buch")
        _save(client, article_id, hund_start, hund_end)
        _save(client, article_id, buch_start, buch_end)

        response = client.get("/api/v1/vocabulary", params={"search": "hun"})

        assert response.status_code == 200
        body = response.json()
        assert [item["lemma"] for item in body["items"]] == ["Hund"]

    def test_pos_filter(self, client: TestClient, db_session: Session, dictionary: None) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client, "Ich rufe dich morgen an. Der Hund schläft.")
        verb_start, verb_end = _token_span(client, article_id, "rufe")
        noun_start, noun_end = _token_span(client, article_id, "Hund")
        _save(client, article_id, verb_start, verb_end)
        _save(client, article_id, noun_start, noun_end)

        response = client.get("/api/v1/vocabulary", params={"pos": "NOUN"})

        assert response.status_code == 200
        assert [item["lemma"] for item in response.json()["items"]] == ["Hund"]

    def test_pagination(self, client: TestClient, db_session: Session, dictionary: None) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client, "Der Hund schläft. Das Buch liegt da.")
        hund_start, hund_end = _token_span(client, article_id, "Hund")
        buch_start, buch_end = _token_span(client, article_id, "Buch")
        _save(client, article_id, hund_start, hund_end)
        _save(client, article_id, buch_start, buch_end)

        response = client.get("/api/v1/vocabulary", params={"page": 1, "page_size": 1})

        assert response.status_code == 200
        body = response.json()
        assert len(body["items"]) == 1
        assert body["total"] == 2

    def test_does_not_list_other_users_items(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client, "Der Hund schläft.")
        start, end = _token_span(client, article_id, "Hund")
        _save(client, article_id, start, end)
        client.post("/api/v1/auth/logout")

        _login_as(client, db_session, username="bailey_jones", email="bailey@example.com")
        response = client.get("/api/v1/vocabulary")

        assert response.status_code == 200
        assert response.json()["items"] == []


class TestGetEditDeleteVocabulary:
    def _save_hund(self, client: TestClient, db_session: Session) -> tuple[str, str]:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client, "Der Hund schläft.")
        start, end = _token_span(client, article_id, "Hund")
        item_id = _save(client, article_id, start, end).json()["item"]["id"]
        return article_id, item_id

    def test_get_item_includes_occurrences(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        article_id, item_id = self._save_hund(client, db_session)

        response = client.get(f"/api/v1/vocabulary/{item_id}")

        assert response.status_code == 200
        body = response.json()
        assert len(body["occurrences"]) == 1
        assert body["occurrences"][0]["article_id"] == article_id

    def test_patch_updates_editable_fields(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _, item_id = self._save_hund(client, db_session)

        response = client.patch(
            f"/api/v1/vocabulary/{item_id}",
            json={"meaning": "my own note on meaning", "notes": "remember this one"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["meaning"] == "my own note on meaning"
        assert body["notes"] == "remember this one"

    def test_delete_removes_item(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _, item_id = self._save_hund(client, db_session)

        delete_response = client.delete(f"/api/v1/vocabulary/{item_id}")
        assert delete_response.status_code == 204

        get_response = client.get(f"/api/v1/vocabulary/{item_id}")
        assert get_response.status_code == 404

    def test_other_user_cannot_get_edit_or_delete(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _, item_id = self._save_hund(client, db_session)
        client.post("/api/v1/auth/logout")

        _login_as(client, db_session, username="bailey_jones", email="bailey@example.com")
        assert client.get(f"/api/v1/vocabulary/{item_id}").status_code == 404
        assert client.patch(f"/api/v1/vocabulary/{item_id}", json={"notes": "x"}).status_code == 404
        assert client.delete(f"/api/v1/vocabulary/{item_id}").status_code == 404


class TestArticleDeletionPolicy:
    def test_deleting_article_keeps_item_removes_occurrence(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client, "Der Hund schläft.")
        start, end = _token_span(client, article_id, "Hund")
        item_id = _save(client, article_id, start, end).json()["item"]["id"]

        delete_response = client.delete(f"/api/v1/articles/{article_id}")
        assert delete_response.status_code == 204

        get_item_response = client.get(f"/api/v1/vocabulary/{item_id}")
        assert get_item_response.status_code == 200
        assert get_item_response.json()["occurrences"] == []
        assert db_session.query(ArticleVocabulary).count() == 0
