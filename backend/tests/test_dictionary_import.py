from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DictionaryEntry, DictionaryForm
from app.scripts.import_dictionary import import_dictionary

FIXTURE_PATH = str(Path(__file__).parent / "fixtures" / "dictionary" / "sample.jsonl")


class TestImportDictionary:
    def test_imports_expected_fields(self, db_session: Session) -> None:
        entry_count, form_count = import_dictionary(FIXTURE_PATH, "test-version", db=db_session)

        # Hund, Buch, anrufen, "vor allem", Kiefer (x2), Tag — chien (not German) and leer
        # (no glosses) are skipped.
        assert entry_count == 7
        assert form_count > 0

        hund = db_session.scalar(select(DictionaryEntry).where(DictionaryEntry.lemma == "Hund"))
        assert hund is not None
        assert hund.pos == "noun"
        assert hund.gender == "Masc"
        assert hund.plural == "Hunde"
        assert hund.glosses == ["dog"]
        assert hund.source == "kaikki-de-extract"
        assert hund.source_version == "test-version"

    def test_keeps_phrase_pos_verbatim(self, db_session: Session) -> None:
        import_dictionary(FIXTURE_PATH, "test-version", db=db_session)

        phrase = db_session.scalar(
            select(DictionaryEntry).where(DictionaryEntry.lemma == "vor allem")
        )
        assert phrase is not None
        assert phrase.pos == "phrase"
        assert "above all" in phrase.glosses

    def test_skips_non_german_entries(self, db_session: Session) -> None:
        import_dictionary(FIXTURE_PATH, "test-version", db=db_session)

        chien = db_session.scalar(select(DictionaryEntry).where(DictionaryEntry.lemma == "chien"))
        assert chien is None

    def test_skips_entries_with_no_glosses(self, db_session: Session) -> None:
        import_dictionary(FIXTURE_PATH, "test-version", db=db_session)

        leer = db_session.scalar(select(DictionaryEntry).where(DictionaryEntry.lemma == "leer"))
        assert leer is None

    def test_keeps_heteronym_pair_as_separate_rows(self, db_session: Session) -> None:
        import_dictionary(FIXTURE_PATH, "test-version", db=db_session)

        kiefer_entries = db_session.scalars(
            select(DictionaryEntry).where(DictionaryEntry.lemma == "Kiefer")
        ).all()
        assert len(kiefer_entries) == 2
        assert {entry.gender for entry in kiefer_entries} == {"Masc", "Fem"}

    def test_imports_inflected_forms(self, db_session: Session) -> None:
        import_dictionary(FIXTURE_PATH, "test-version", db=db_session)

        buch = db_session.scalar(select(DictionaryEntry).where(DictionaryEntry.lemma == "Buch"))
        assert buch is not None
        forms = db_session.scalars(
            select(DictionaryForm).where(DictionaryForm.dictionary_entry_id == buch.id)
        ).all()
        assert {form.form for form in forms} == {"Buches", "Bücher"}

    def test_skips_oversized_form_without_crashing(self, db_session: Session) -> None:
        """Regression test: a real import run against the live kaikki.org dump hit a form
        value over 255 chars (a descriptive note mistagged as a form, not a real inflected
        word) and crashed with a DB column-width error. The entry's own data must still
        import; only the oversized form row is skipped."""
        import_dictionary(FIXTURE_PATH, "test-version", db=db_session)

        tag = db_session.scalar(select(DictionaryEntry).where(DictionaryEntry.lemma == "Tag"))
        assert tag is not None
        assert tag.glosses == ["day"]
        forms = db_session.scalars(
            select(DictionaryForm).where(DictionaryForm.dictionary_entry_id == tag.id)
        ).all()
        assert {form.form for form in forms} == {"Tage"}

    def test_rerun_is_idempotent_and_replaces_prior_data(self, db_session: Session) -> None:
        first_entry_count, first_form_count = import_dictionary(FIXTURE_PATH, "v1", db=db_session)
        second_entry_count, second_form_count = import_dictionary(FIXTURE_PATH, "v2", db=db_session)

        assert first_entry_count == second_entry_count
        assert first_form_count == second_form_count
        assert db_session.query(DictionaryEntry).count() == second_entry_count
        assert {entry.source_version for entry in db_session.query(DictionaryEntry).all()} == {"v2"}
