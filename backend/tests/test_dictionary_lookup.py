from pathlib import Path

import pytest
from factories import make_user
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.scripts.import_dictionary import import_dictionary
from app.services import dictionary_service

FIXTURE_PATH = str(Path(__file__).parent / "fixtures" / "dictionary" / "sample.jsonl")
VALID_PASSWORD = "correct horse battery staple"
SAMPLE_TEXT = "Ich rufe dich morgen an. Der Hund schläft. Vor allem mag ich Bücher."


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


def _create_article(client: TestClient) -> str:
    response = client.post("/api/v1/articles", json={"original_text": SAMPLE_TEXT})
    assert response.status_code == 201
    return response.json()["id"]


def _token_span(client: TestClient, article_id: str, text: str) -> tuple[int, int]:
    analysis = client.get(f"/api/v1/articles/{article_id}/analysis").json()
    for token in analysis["tokens"]:
        if token["text"] == text:
            return token["start"], token["end"]
    raise AssertionError(f"no token with text {text!r} in analysis")


class TestLookupService:
    def test_lookup_by_lemma_and_pos(self, db_session: Session, dictionary: None) -> None:
        entry = dictionary_service.lookup(db_session, "Hund", "noun")

        assert entry is not None
        assert entry.gender == "Masc"
        assert entry.plural == "Hunde"

    def test_lookup_falls_back_to_lemma_only_when_pos_does_not_match(
        self, db_session: Session, dictionary: None
    ) -> None:
        entry = dictionary_service.lookup(db_session, "Hund", "verb")

        assert entry is not None
        assert entry.lemma == "Hund"

    def test_lookup_returns_none_when_no_entry(self, db_session: Session, dictionary: None) -> None:
        assert dictionary_service.lookup(db_session, "Fahrradweg", "noun") is None

    def test_lookup_by_surface_form_falls_back_to_forms_index(
        self, db_session: Session, dictionary: None
    ) -> None:
        entry = dictionary_service.lookup_by_surface_form(db_session, "Bücher")

        assert entry is not None
        assert entry.lemma == "Buch"

    def test_lookup_by_surface_form_returns_none_when_no_form_matches(
        self, db_session: Session, dictionary: None
    ) -> None:
        assert dictionary_service.lookup_by_surface_form(db_session, "Nichtexistent") is None

    def test_lookup_phrase_found(self, db_session: Session, dictionary: None) -> None:
        entry = dictionary_service.lookup_phrase(db_session, "Vor allem")

        assert entry is not None
        assert "above all" in entry.glosses

    def test_lookup_phrase_not_found_returns_none_never_a_guess(
        self, db_session: Session, dictionary: None
    ) -> None:
        assert dictionary_service.lookup_phrase(db_session, "auf jeden Fall") is None


class TestDictionaryEndpoint:
    def test_noun_lookup_includes_gender_and_plural(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client)
        start, end = _token_span(client, article_id, "Hund")

        response = client.get(
            f"/api/v1/articles/{article_id}/dictionary", params={"start": start, "end": end}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["entry"]["gender"] == "Masc"
        assert body["entry"]["plural"] == "Hunde"
        assert body["entry"]["article"] == "der"
        assert body["entry"]["source_label"] == "dictionary"

    def test_plural_only_noun_gets_die_article_with_no_gender(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = client.post(
            "/api/v1/articles", json={"original_text": "Die Eltern sind da."}
        ).json()["id"]
        start, end = _token_span(client, article_id, "Eltern")

        response = client.get(
            f"/api/v1/articles/{article_id}/dictionary", params={"start": start, "end": end}
        )

        assert response.status_code == 200
        entry = response.json()["entry"]
        assert entry["gender"] is None
        assert entry["article"] == "die"

    def test_separable_verb_uses_combined_lemma(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client)
        start, end = _token_span(client, article_id, "rufe")

        response = client.get(
            f"/api/v1/articles/{article_id}/dictionary", params={"start": start, "end": end}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["lemma"] == "anrufen"
        assert body["is_separable_verb"] is True
        assert body["entry"] is not None
        assert "to call (by phone)" in body["entry"]["glosses"]

    def test_multi_word_phrase_lookup(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client)
        vor_start, _ = _token_span(client, article_id, "Vor")
        _, allem_end = _token_span(client, article_id, "allem")

        response = client.get(
            f"/api/v1/articles/{article_id}/dictionary",
            params={"start": vor_start, "end": allem_end},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["entry"] is not None
        assert "above all" in body["entry"]["glosses"]

    def test_no_entry_returns_null_not_an_error(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client)
        start, end = _token_span(client, article_id, "morgen")

        response = client.get(
            f"/api/v1/articles/{article_id}/dictionary", params={"start": start, "end": end}
        )

        assert response.status_code == 200
        assert response.json()["entry"] is None

    def test_other_user_gets_404(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client)
        client.post("/api/v1/auth/logout")

        _login_as(client, db_session, username="bailey_jones", email="bailey@example.com")
        response = client.get(
            f"/api/v1/articles/{article_id}/dictionary", params={"start": 0, "end": 3}
        )

        assert response.status_code == 404

    def test_unverified_user_gets_403(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        make_user(
            db_session, email="alex@example.com", username="alex_morgan", password=VALID_PASSWORD
        )
        client.post(
            "/api/v1/auth/login",
            json={"identifier": "alex_morgan", "password": VALID_PASSWORD},
        )

        response = client.get(
            "/api/v1/articles/00000000-0000-0000-0000-000000000000/dictionary",
            params={"start": 0, "end": 3},
        )

        assert response.status_code == 403
