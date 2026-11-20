"""Anki-style card data: meanings snapshot/merge, song line context and its translation, the
DeepL failure + retry path, editing, the due-card payload, and the one-off backfill."""

from pathlib import Path

import pytest
from factories import make_article, make_song, make_user
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ArticleVocabulary, User, VocabularyItem
from app.scripts.backfill_vocabulary_cards import backfill
from app.scripts.import_dictionary import import_dictionary
from app.services.translation.fake_provider import FakeTranslationProvider
from app.services.translation.provider import TranslationProviderError, TranslationTimeoutError

FIXTURE_PATH = str(Path(__file__).parent / "fixtures" / "dictionary" / "cards.jsonl")
VALID_PASSWORD = "correct horse battery staple"

# Invented lyric-style lines — never real copyrighted lyrics (see CLAUDE.md, ADR 0006).
LYRICS = (
    "[Strophe 1]\n"
    "Die Scheine liegen auf dem Tisch\n"
    "Ich ging allein durch die Nacht\n"
    "\n"
    "[Hook]\n"
    "Die Sterne sehen alles"
)
LINE_1 = "Die Scheine liegen auf dem Tisch"
LINE_2 = "Ich ging allein durch die Nacht"
LINE_3 = "Die Sterne sehen alles"


@pytest.fixture
def dictionary(db_session: Session) -> None:
    import_dictionary(FIXTURE_PATH, "test-version", db=db_session)


def _login_as(
    client: TestClient, db_session: Session, *, username: str = "alex", email: str = "a@example.com"
) -> User:
    user = make_user(
        db_session, email=email, username=username, password=VALID_PASSWORD, email_verified=True
    )
    response = client.post(
        "/api/v1/auth/login", json={"identifier": username, "password": VALID_PASSWORD}
    )
    assert response.status_code == 200
    return user


def _span(text: str, word: str, occurrence: int = 0) -> tuple[int, int]:
    start = -1
    for _ in range(occurrence + 1):
        start = text.index(word, start + 1)
    return start, start + len(word)


def _save(client: TestClient, article_id, start: int, end: int):
    return client.post(
        "/api/v1/vocabulary", json={"article_id": str(article_id), "start": start, "end": end}
    )


def _song(db_session: Session, user: User):
    return make_song(db_session, user, lyrics=LYRICS)


class TestSaveSnapshotsCardData:
    def test_song_save_snapshots_meanings_and_line_translation(
        self,
        client: TestClient,
        db_session: Session,
        dictionary: None,
        fake_translation_provider: FakeTranslationProvider,
    ) -> None:
        user = _login_as(client, db_session)
        song = _song(db_session, user)

        response = _save(client, song.id, *_span(LYRICS, "Scheine"))

        assert response.status_code == 201
        body = response.json()
        assert body["translation_pending"] is False
        item = body["item"]
        assert item["lemma"] == "Schein"
        # Contextual DeepL translation first, then the dictionary's English translations
        # ("Shine" from sense 2 is a case-insensitive duplicate of "shine" and dropped).
        assert item["meanings"] == [
            {"text": "[EN-US] Scheine", "source": "machine", "sense_label": None},
            {"text": "shine", "source": "dictionary", "sense_label": "schwaches Leuchten"},
            {"text": "gleam", "source": "dictionary", "sense_label": "schwaches Leuchten"},
            {
                "text": "certificate",
                "source": "dictionary",
                "sense_label": "Bescheinigung, Geldnote",
            },
        ]
        # Deprecated fields are still dual-written.
        assert item["translation"] == "[EN-US] Scheine"
        assert item["meaning"] == "schwaches Leuchten"
        assert item["example_occurrence_id"] == body["occurrence_id"]

        # The word is translated in the context of its line; the line with its neighbouring
        # line (the "[Strophe 1]" header is never context) as DeepL context.
        assert ("Scheine", LINE_1, "EN-US") in fake_translation_provider.calls
        assert (LINE_1, LINE_2, "EN-US") in fake_translation_provider.calls

        detail = client.get(f"/api/v1/vocabulary/{item['id']}").json()
        occurrence = detail["occurrences"][0]
        assert occurrence["context_line"] == LINE_1
        assert occurrence["context_sentence"] == LINE_1
        assert occurrence["context_translation"] == f"[EN-US] {LINE_1}"
        assert occurrence["needs_translation"] is False

    def test_text_article_keeps_the_sentence_as_context(
        self,
        client: TestClient,
        db_session: Session,
        dictionary: None,
        fake_translation_provider: FakeTranslationProvider,
    ) -> None:
        user = _login_as(client, db_session)
        text = "Der Schein trügt. Die Nacht ist lang."
        article = make_article(db_session, user, original_text=text)

        item = _save(client, article.id, *_span(text, "Nacht")).json()["item"]

        detail = client.get(f"/api/v1/vocabulary/{item['id']}").json()
        assert detail["occurrences"][0]["context_line"] == "Die Nacht ist lang."
        # A text sentence is translated on its own, exactly as /translate always did.
        assert ("Die Nacht ist lang.", None, "EN-US") in fake_translation_provider.calls

    def test_resave_adds_the_occurrence_and_merges_new_meanings_without_duplicates(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        user = _login_as(client, db_session)
        song = _song(db_session, user)
        text = "Der Schein trügt."
        article = make_article(db_session, user, original_text=text)

        first = _save(client, song.id, *_span(LYRICS, "Scheine")).json()
        second = _save(client, article.id, *_span(text, "Schein")).json()

        assert second["item"]["id"] == first["item"]["id"]
        assert second["already_saved"] is False
        texts = [meaning["text"] for meaning in second["item"]["meanings"]]
        assert texts == ["[EN-US] Scheine", "shine", "gleam", "certificate", "[EN-US] Schein"]
        # The card example stays the first occurrence saved.
        assert second["item"]["example_occurrence_id"] == first["occurrence_id"]
        detail = client.get(f"/api/v1/vocabulary/{first['item']['id']}").json()
        assert len(detail["occurrences"]) == 2

    def test_user_translation_language_picks_dictionary_language(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        user = _login_as(client, db_session)
        user.translation_language = "ES"
        db_session.flush()
        song = _song(db_session, user)

        item = _save(client, song.id, *_span(LYRICS, "Sterne")).json()["item"]

        assert [m["text"] for m in item["meanings"]] == ["[ES] Sterne", "estrella"]


class TestCrossLineSelections:
    def test_selection_spanning_two_lyric_lines_is_rejected(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        user = _login_as(client, db_session)
        song = _song(db_session, user)
        start, _ = _span(LYRICS, "Tisch")
        _, end = _span(LYRICS, "Ich")

        for response in (
            _save(client, song.id, start, end),
            client.get(
                f"/api/v1/articles/{song.id}/dictionary", params={"start": start, "end": end}
            ),
            client.post(f"/api/v1/articles/{song.id}/translate", json={"start": start, "end": end}),
        ):
            assert response.status_code == 422
            assert response.json()["detail"]["code"] == "selection_spans_lines"

    def test_section_header_is_never_a_context_line(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        user = _login_as(client, db_session)
        song = _song(db_session, user)

        response = _save(client, song.id, *_span(LYRICS, "Hook"))

        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "selection_not_in_lyric_line"

    def test_translate_endpoint_returns_the_line_translation_for_songs(
        self,
        client: TestClient,
        db_session: Session,
        dictionary: None,
        fake_translation_provider: FakeTranslationProvider,
    ) -> None:
        user = _login_as(client, db_session)
        song = _song(db_session, user)
        start, end = _span(LYRICS, "Sterne")

        response = client.post(
            f"/api/v1/articles/{song.id}/translate",
            json={"start": start, "end": end, "include_sentence": True},
        )

        assert response.status_code == 200
        assert response.json()["sentence_translation"] == f"[EN-US] {LINE_3}"
        # Last line: only the previous line (across the blank line and header) is context.
        assert (LINE_3, LINE_2, "EN-US") in fake_translation_provider.calls


class TestDeepLFailureAndRetry:
    def test_deepl_failure_saves_without_translation_and_retry_fills_it(
        self,
        client: TestClient,
        db_session: Session,
        dictionary: None,
        fake_translation_provider: FakeTranslationProvider,
    ) -> None:
        user = _login_as(client, db_session)
        song = _song(db_session, user)
        fake_translation_provider.fail_with = TranslationProviderError()

        saved = _save(client, song.id, *_span(LYRICS, "Scheine"))

        assert saved.status_code == 201
        body = saved.json()
        assert body["translation_pending"] is True
        assert [m["source"] for m in body["item"]["meanings"]] == ["dictionary"] * 3
        assert body["item"]["translation"] is None
        detail = client.get(f"/api/v1/vocabulary/{body['item']['id']}").json()
        assert detail["occurrences"][0]["needs_translation"] is True
        assert detail["occurrences"][0]["context_line"] == LINE_1

        fake_translation_provider.fail_with = None
        retried = client.post(
            f"/api/v1/vocabulary/occurrences/{body['occurrence_id']}/retry-translation"
        )

        assert retried.status_code == 200
        assert retried.json()["context_translation"] == f"[EN-US] {LINE_1}"
        assert retried.json()["needs_translation"] is False
        item = client.get(f"/api/v1/vocabulary/{body['item']['id']}").json()
        assert item["meanings"][0] == {
            "text": "[EN-US] Scheine",
            "source": "machine",
            "sense_label": None,
        }
        assert len(item["meanings"]) == 4
        assert item["translation"] == "[EN-US] Scheine"

    def test_retry_surfaces_the_translation_error_code(
        self,
        client: TestClient,
        db_session: Session,
        dictionary: None,
        fake_translation_provider: FakeTranslationProvider,
    ) -> None:
        user = _login_as(client, db_session)
        song = _song(db_session, user)
        fake_translation_provider.fail_with = TranslationTimeoutError()
        body = _save(client, song.id, *_span(LYRICS, "Scheine")).json()

        response = client.post(
            f"/api/v1/vocabulary/occurrences/{body['occurrence_id']}/retry-translation"
        )

        assert response.status_code == 504
        assert response.json()["detail"]["code"] == "translation_timeout"

    def test_retry_is_a_noop_when_nothing_is_missing(
        self,
        client: TestClient,
        db_session: Session,
        dictionary: None,
        fake_translation_provider: FakeTranslationProvider,
    ) -> None:
        user = _login_as(client, db_session)
        song = _song(db_session, user)
        body = _save(client, song.id, *_span(LYRICS, "Scheine")).json()
        calls_before = len(fake_translation_provider.calls)

        response = client.post(
            f"/api/v1/vocabulary/occurrences/{body['occurrence_id']}/retry-translation"
        )

        assert response.status_code == 200
        assert len(fake_translation_provider.calls) == calls_before

    def test_other_users_occurrence_is_404(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        owner = make_user(db_session, email="owner@example.com", username="owner")
        song = _song(db_session, owner)
        item = VocabularyItem(
            user_id=owner.id, lemma="Schein", display_form="Scheine", part_of_speech="NOUN"
        )
        db_session.add(item)
        db_session.flush()
        start, end = _span(LYRICS, "Scheine")
        occurrence = ArticleVocabulary(
            article_id=song.id,
            vocabulary_item_id=item.id,
            start_offset=start,
            end_offset=end,
            context_sentence=LINE_1,
        )
        db_session.add(occurrence)
        db_session.flush()
        _login_as(client, db_session, username="intruder", email="i@example.com")

        for response in (
            client.post(f"/api/v1/vocabulary/occurrences/{occurrence.id}/retry-translation"),
            client.patch(
                f"/api/v1/vocabulary/occurrences/{occurrence.id}",
                json={"context_translation": "hijacked"},
            ),
        ):
            assert response.status_code == 404


class TestEditing:
    def test_patch_meanings_reorders_removes_adds_and_dedupes(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        user = _login_as(client, db_session)
        song = _song(db_session, user)
        item = _save(client, song.id, *_span(LYRICS, "Scheine")).json()["item"]

        response = client.patch(
            f"/api/v1/vocabulary/{item['id']}",
            json={
                "meanings": [
                    {"text": "certificate", "source": "dictionary"},
                    {"text": "banknote", "source": "machine"},
                    {"text": "Certificate", "source": "machine"},
                ]
            },
        )

        assert response.status_code == 200
        assert [m["text"] for m in response.json()["meanings"]] == ["certificate", "banknote"]

    def test_patch_example_occurrence_must_belong_to_the_item(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        user = _login_as(client, db_session)
        song = _song(db_session, user)
        text = "Der Schein trügt. Die Nacht ist lang."
        article = make_article(db_session, user, original_text=text)
        schein = _save(client, song.id, *_span(LYRICS, "Scheine")).json()
        second = _save(client, article.id, *_span(text, "Schein")).json()
        nacht = _save(client, article.id, *_span(text, "Nacht")).json()

        invalid = client.patch(
            f"/api/v1/vocabulary/{schein['item']['id']}",
            json={"example_occurrence_id": nacht["occurrence_id"]},
        )
        valid = client.patch(
            f"/api/v1/vocabulary/{schein['item']['id']}",
            json={"example_occurrence_id": second["occurrence_id"]},
        )

        assert invalid.status_code == 422
        assert invalid.json()["detail"]["code"] == "invalid_example_occurrence"
        assert valid.status_code == 200
        assert valid.json()["example_occurrence_id"] == second["occurrence_id"]

    def test_patch_occurrence_context_translation(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        user = _login_as(client, db_session)
        song = _song(db_session, user)
        body = _save(client, song.id, *_span(LYRICS, "Scheine")).json()

        response = client.patch(
            f"/api/v1/vocabulary/occurrences/{body['occurrence_id']}",
            json={"context_translation": "  The bills are lying on the table  "},
        )

        assert response.status_code == 200
        assert response.json()["context_translation"] == "The bills are lying on the table"


class TestDueCardPayload:
    def test_song_card_front_and_back(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        user = _login_as(client, db_session)
        song = _song(db_session, user)
        _save(client, song.id, *_span(LYRICS, "Scheine"))

        card = client.get("/api/v1/reviews/due").json()["items"][0]

        assert card["front"]["display"] == "der Schein, -e"
        assert card["front"]["part_of_speech"] == "NOUN"
        back = card["back"]
        assert [m["text"] for m in back["meanings"]] == [
            "[EN-US] Scheine",
            "shine",
            "gleam",
            "certificate",
        ]
        assert back["meanings"][0]["source"] == "machine"
        example = back["example"]
        assert example["line"] == LINE_1
        assert example["translation"] == f"[EN-US] {LINE_1}"
        assert LINE_1[example["highlight_start"] : example["highlight_end"]] == "Scheine"
        assert example["song"] == {
            "title": "Nachtlicht",
            "artist": "Die Erfundenen",
            "cover_url": "https://images.genius.com/example-cover.jpg",
        }

    def test_text_card_has_no_song_and_uses_the_chosen_example(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        user = _login_as(client, db_session)
        text = "Die Nacht ist lang. Jede Nacht ist kalt."
        article = make_article(db_session, user, original_text=text)
        first = _save(client, article.id, *_span(text, "Nacht")).json()
        second = _save(client, article.id, *_span(text, "Nacht", occurrence=1)).json()
        client.patch(
            f"/api/v1/vocabulary/{first['item']['id']}",
            json={"example_occurrence_id": second["occurrence_id"]},
        )

        card = client.get("/api/v1/reviews/due").json()["items"][0]

        assert card["front"]["display"] == "die Nacht, -¨e"
        example = card["back"]["example"]
        assert example["line"] == "Jede Nacht ist kalt."
        assert example["song"] is None
        assert example["line"][example["highlight_start"] : example["highlight_end"]] == "Nacht"

    def test_verb_card_shows_the_infinitive(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        user = _login_as(client, db_session)
        song = _song(db_session, user)
        _save(client, song.id, *_span(LYRICS, "ging"))

        card = client.get("/api/v1/reviews/due").json()["items"][0]

        assert card["front"]["display"] == "gehen"
        assert card["front"]["part_of_speech"] in {"VERB", "AUX"}


class TestBackfill:
    def _legacy_item(self, client: TestClient, db_session: Session, user: User) -> VocabularyItem:
        """A saved word with its card fields wiped, as rows saved before them look."""
        song = _song(db_session, user)
        item_id = _save(client, song.id, *_span(LYRICS, "Scheine")).json()["item"]["id"]
        item = db_session.get(VocabularyItem, item_id)
        item.meanings = []
        item.example_occurrence_id = None
        for occurrence in db_session.scalars(
            select(ArticleVocabulary).where(ArticleVocabulary.vocabulary_item_id == item.id)
        ):
            occurrence.context_line = None
            occurrence.context_translation = None
        db_session.commit()
        return item

    def test_backfill_fills_card_fields_and_is_idempotent(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        user = _login_as(client, db_session)
        item = self._legacy_item(client, db_session, user)
        provider = FakeTranslationProvider()

        first = backfill(db_session, provider)

        db_session.refresh(item)
        occurrence = db_session.scalar(
            select(ArticleVocabulary).where(ArticleVocabulary.vocabulary_item_id == item.id)
        )
        assert occurrence.context_line == LINE_1
        assert occurrence.context_translation == f"[EN-US] {LINE_1}"
        assert item.example_occurrence_id == occurrence.id
        assert [m["text"] for m in item.meanings] == [
            "[EN-US] Scheine",
            "shine",
            "gleam",
            "certificate",
        ]
        assert first.context_lines_filled == 1
        assert first.meanings_filled == 1
        assert first.examples_filled == 1
        # The line translation was already in translation_cache from the original save, so
        # the backfill reused it instead of billing DeepL again.
        assert first.context_translations_filled == 1
        assert first.deepl_characters == 0

        second = backfill(db_session, provider)

        assert second.context_lines_filled == 0
        assert second.context_translations_filled == 0
        assert second.meanings_filled == 0
        assert second.examples_filled == 0
        assert second.deepl_calls == 0

    def test_backfill_counts_billed_characters_and_survives_deepl_failures(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        user = _login_as(client, db_session)
        text = "Die Nacht ist lang."
        article = make_article(db_session, user, original_text=text)
        failing = FakeTranslationProvider(fail_with=TranslationProviderError())
        item = VocabularyItem(
            user_id=user.id,
            lemma="Nacht",
            display_form="Nacht",
            part_of_speech="NOUN",
            grammar_metadata={},
        )
        db_session.add(item)
        db_session.flush()
        start, end = _span(text, "Nacht")
        db_session.add(
            ArticleVocabulary(
                article_id=article.id,
                vocabulary_item_id=item.id,
                start_offset=start,
                end_offset=end,
                context_sentence=text,
            )
        )
        db_session.commit()

        failed = backfill(db_session, failing)
        assert failed.context_translations_failed == 1
        assert failed.context_lines_filled == 1

        working = FakeTranslationProvider()
        retried = backfill(db_session, working)
        assert retried.context_translations_filled == 1
        assert retried.deepl_calls == 1
        assert retried.deepl_characters == len(text)
