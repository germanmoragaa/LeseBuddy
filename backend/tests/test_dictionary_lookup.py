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


CARDS_FIXTURE_PATH = str(Path(__file__).parent / "fixtures" / "dictionary" / "cards.jsonl")


@pytest.fixture
def cards_dictionary(db_session: Session) -> None:
    import_dictionary(CARDS_FIXTURE_PATH, "test-version", db=db_session)


class TestFormOfPreference:
    """Regression: "Scheine" (spaCy lemma "Schein", NOUN) showed "2. Person Singular
    Imperativ ... des Verbs scheinen" - spaCy's NOUN never matched the dataset's "noun", and
    the lemma-only fallback picked the form-of verb entry "schein"."""

    def test_spacy_upos_matches_the_dataset_pos(
        self, db_session: Session, cards_dictionary: None
    ) -> None:
        entry = dictionary_service.lookup(db_session, "Schein", "NOUN")

        assert entry is not None
        assert (entry.lemma, entry.pos, entry.form_of_lemma) == ("Schein", "noun", None)

    def test_lemma_only_fallback_never_returns_a_form_of_entry(
        self, db_session: Session, cards_dictionary: None
    ) -> None:
        # "X" has no dataset equivalent -> lemma-only; still the real noun, not "schein" (verb).
        entry = dictionary_service.lookup(db_session, "schein", "X")

        assert entry is not None
        assert entry.form_of_lemma is None
        assert entry.lemma == "Schein"

    def test_form_of_entry_alone_is_not_a_lemma_match(
        self, db_session: Session, cards_dictionary: None
    ) -> None:
        assert dictionary_service.lookup(db_session, "ging", "VERB") is None

    def test_surface_form_fallback_resolves_form_of_to_its_base_lemma(
        self, db_session: Session, cards_dictionary: None
    ) -> None:
        entry = dictionary_service.lookup_by_surface_form(db_session, "ging", "VERB")

        assert entry is not None
        assert (entry.lemma, entry.pos) == ("gehen", "verb")

    def test_surface_form_fallback_prefers_matching_pos_in_forms_index(
        self, db_session: Session, cards_dictionary: None
    ) -> None:
        entry = dictionary_service.lookup_by_surface_form(db_session, "Häuser", "NOUN")

        assert entry is not None
        assert (entry.lemma, entry.form_of_lemma) == ("Haus", None)

    @pytest.mark.parametrize(
        ("word", "expected_lemma", "expected_pos"),
        [("Scheine", "Schein", "noun"), ("Häuser", "Haus", "noun"), ("ging", "gehen", "verb")],
    )
    def test_endpoint_resolves_inflected_words_to_their_base_entry(
        self,
        client: TestClient,
        db_session: Session,
        cards_dictionary: None,
        word: str,
        expected_lemma: str,
        expected_pos: str,
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = client.post(
            "/api/v1/articles",
            # No separable particle anywhere: "ging ... heran" would (correctly) resolve
            # as the separable verb "herangehen" instead.
            json={"original_text": "Die Scheine lagen dort. Ich ging allein. Die Häuser sind alt."},
        ).json()["id"]
        start, end = _token_span(client, article_id, word)

        response = client.get(
            f"/api/v1/articles/{article_id}/dictionary", params={"start": start, "end": end}
        )

        assert response.status_code == 200
        entry = response.json()["entry"]
        assert entry is not None
        assert entry["pos"] == expected_pos
        assert not any("Person Singular" in gloss for gloss in entry["glosses"])
        if expected_lemma == "Schein":
            assert entry["article"] == "der"
            assert entry["plural"] == "Scheine"

    def test_endpoint_includes_dictionary_translations_in_the_users_language(
        self, client: TestClient, db_session: Session, cards_dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = client.post(
            "/api/v1/articles", json={"original_text": "Der Schein trügt."}
        ).json()["id"]
        start, end = _token_span(client, article_id, "Schein")

        entry = client.get(
            f"/api/v1/articles/{article_id}/dictionary", params={"start": start, "end": end}
        ).json()["entry"]

        # EN-US user: English only, sense 1 then sense 2, source order within a sense.
        assert [t["text"] for t in entry["translations"]] == [
            "shine",
            "gleam",
            "certificate",
            "Shine",
        ]
        assert entry["translations"][2]["sense_label"] == "Bescheinigung, Geldnote"


@pytest.mark.parametrize(
    ("upos", "expected"),
    [
        ("NOUN", ("noun",)),
        ("PROPN", ("name", "noun")),
        ("VERB", ("verb",)),
        ("AUX", ("verb",)),
        ("ADJ", ("adj",)),
        ("ADV", ("adv",)),
        ("ADP", ("prep", "postp")),
        ("PRON", ("pron",)),
        ("DET", ("det",)),
        ("NUM", ("num",)),
        ("CCONJ", ("conj",)),
        ("SCONJ", ("conj",)),
        ("PART", ("particle",)),
        ("INTJ", ("intj",)),
        ("X", ()),
        ("PUNCT", ()),
        ("noun", ("noun",)),
    ],
)
def test_upos_to_dataset_pos(upos: str, expected: tuple[str, ...]) -> None:
    assert dictionary_service.dataset_pos_for(upos) == expected
