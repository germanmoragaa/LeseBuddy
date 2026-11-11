from pathlib import Path

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

import app.scripts.import_dictionary as import_dictionary_module
from app.models import DictionaryEntry, DictionaryForm
from app.scripts.import_dictionary import import_dictionary

FIXTURE_PATH = str(Path(__file__).parent / "fixtures" / "dictionary" / "sample.jsonl")


class TestImportDictionary:
    def test_imports_expected_fields(self, db_session: Session) -> None:
        entry_count, form_count = import_dictionary(FIXTURE_PATH, "test-version", db=db_session)

        # Hund, Buch, Universitaet, anrufen, "vor allem", Kiefer (x2), Eltern, Tag - chien
        # (not German) and leer (no glosses) are skipped.
        assert entry_count == 9
        assert form_count > 0

        hund = db_session.scalar(select(DictionaryEntry).where(DictionaryEntry.lemma == "Hund"))
        assert hund is not None
        assert hund.pos == "noun"
        assert hund.gender == "Masc"
        assert hund.plural_only is False
        assert hund.plural == "Hunde"
        assert hund.glosses == ["dog"]
        assert hund.source == "kaikki-de-extract"
        assert hund.source_version == "test-version"

    def test_extracts_gender_from_top_level_tags_not_sense_tags(self, db_session: Session) -> None:
        """Regression test: the real kaikki.org dump tags noun gender on the entry's
        top-level `tags` list, not inside any sense's own `tags` - a prior version of the
        import mapping only scanned senses[].tags, which left gender null for virtually every
        real noun (confirmed against the live dump: ~0% coverage) despite passing its own
        fixture-based tests, because that fixture encoded gender in the wrong place too."""
        import_dictionary(FIXTURE_PATH, "test-version", db=db_session)

        universitaet = db_session.scalar(
            select(DictionaryEntry).where(DictionaryEntry.lemma == "Universität")
        )
        assert universitaet is not None
        assert universitaet.gender == "Fem"
        assert universitaet.plural_only is False

        buch = db_session.scalar(select(DictionaryEntry).where(DictionaryEntry.lemma == "Buch"))
        assert buch is not None
        assert buch.gender == "Neut"

    def test_plurale_tantum_noun_has_no_gender_but_is_flagged_plural_only(
        self, db_session: Session
    ) -> None:
        """ "Eltern" (parents) has no top-level gender tag and only plural-tagged forms (no
        singular exists) - a genuine plurale tantum, not just missing data. Flagged so the
        API can still show the nominative article ("die") despite there being no gender."""
        import_dictionary(FIXTURE_PATH, "test-version", db=db_session)

        eltern = db_session.scalar(select(DictionaryEntry).where(DictionaryEntry.lemma == "Eltern"))
        assert eltern is not None
        assert eltern.gender is None
        assert eltern.plural_only is True

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

    def test_live_tables_are_unaffected_while_staging_tables_are_populated(
        self, db_session: Session
    ) -> None:
        """The staging tables are separate objects from the live ones until the swap — a read
        against the live tables mid-import (simulated here by just checking them right after
        `_create_staging_tables`, before any streaming/insert happens) must see the
        pre-import data untouched, never a lock or a partial truncate."""
        import_dictionary(FIXTURE_PATH, "v1", db=db_session)
        baseline_count = db_session.query(DictionaryEntry).count()
        assert baseline_count > 0

        import_dictionary_module._create_staging_tables(db_session)
        try:
            assert db_session.query(DictionaryEntry).count() == baseline_count
        finally:
            import_dictionary_module._drop_staging_tables(db_session)

    def test_staging_tables_copy_the_live_indexes(self, db_session: Session) -> None:
        import_dictionary_module._create_staging_tables(db_session)
        try:
            index_count = db_session.scalar(
                text(
                    "SELECT count(*) FROM pg_indexes WHERE tablename = 'dictionary_entries_staging'"
                )
            )
            assert index_count >= 2  # primary key + ix_..._lemma_lower
        finally:
            import_dictionary_module._drop_staging_tables(db_session)

    def test_swap_adds_back_the_foreign_key_from_forms_to_entries(
        self, db_session: Session
    ) -> None:
        import_dictionary(FIXTURE_PATH, "v1", db=db_session)

        fk_count = db_session.scalar(
            text(
                "SELECT count(*) FROM information_schema.table_constraints "
                "WHERE table_name = 'dictionary_forms' AND constraint_type = 'FOREIGN KEY'"
            )
        )
        assert fk_count == 1

    def test_failure_mid_import_leaves_no_staging_tables_and_prior_data_intact(
        self, db_session: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import_dictionary(FIXTURE_PATH, "v1", db=db_session)
        baseline_entries = db_session.query(DictionaryEntry).count()
        baseline_forms = db_session.query(DictionaryForm).count()

        def boom(*args: object, **kwargs: object) -> None:
            raise RuntimeError("simulated failure mid-import")

        monkeypatch.setattr(import_dictionary_module, "_finalize_and_swap_staging_tables", boom)

        with pytest.raises(RuntimeError, match="simulated failure mid-import"):
            import_dictionary(FIXTURE_PATH, "v2", db=db_session)

        # Rolled back entirely: no leaked staging tables, and the live data is still v1's.
        staging_table_count = db_session.scalar(
            text(
                "SELECT count(*) FROM pg_tables "
                "WHERE tablename IN ('dictionary_entries_staging', 'dictionary_forms_staging')"
            )
        )
        assert staging_table_count == 0
        assert db_session.query(DictionaryEntry).count() == baseline_entries
        assert db_session.query(DictionaryForm).count() == baseline_forms
        assert {entry.source_version for entry in db_session.query(DictionaryEntry).all()} == {"v1"}

    def test_keyboard_interrupt_mid_import_leaves_no_staging_tables_and_prior_data_intact(
        self, db_session: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import_dictionary(FIXTURE_PATH, "v1", db=db_session)
        baseline_entries = db_session.query(DictionaryEntry).count()

        def interrupt(*args: object, **kwargs: object) -> None:
            raise KeyboardInterrupt

        monkeypatch.setattr(
            import_dictionary_module, "_finalize_and_swap_staging_tables", interrupt
        )

        with pytest.raises(KeyboardInterrupt):
            import_dictionary(FIXTURE_PATH, "v2", db=db_session)

        staging_table_count = db_session.scalar(
            text(
                "SELECT count(*) FROM pg_tables "
                "WHERE tablename IN ('dictionary_entries_staging', 'dictionary_forms_staging')"
            )
        )
        assert staging_table_count == 0
        assert db_session.query(DictionaryEntry).count() == baseline_entries
        assert {entry.source_version for entry in db_session.query(DictionaryEntry).all()} == {"v1"}
