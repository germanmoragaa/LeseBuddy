"""Imports German dictionary data into dictionary_entries/dictionary_forms/dictionary_translations.

    uv run python -m app.scripts.import_dictionary [--source PATH_OR_URL] [--source-version TAG]

Source: kaikki.org's German-Wiktionary extract (`de-extract.jsonl.gz`: German glosses, plus
each entry's "Übersetzungen" section, of which only TRANSLATION_LANGS are kept — see
docs/decisions/0004-translations-and-dictionary.md). Streams the gzip JSONL file line by line
(never loads the whole file into memory) and batches Core `INSERT` statements (not one ORM
`session.add()` per row — the per-row ORM overhead made the real ~1.3M-line dump take upwards
of 10 hours; batched `executemany`-style inserts are the fix).

Loads into freshly-created `dictionary_entries_staging`/`dictionary_forms_staging` tables
(same columns/indexes as the live tables, via `LIKE ... INCLUDING ALL`) rather than truncating
the live tables up front — the live tables stay fully readable for the entire, potentially
long, streaming-insert phase. Only the final swap (`ALTER TABLE ... RENAME`, a metadata-only
operation) takes an exclusive lock on the live tables, for milliseconds, not the whole import.
Everything — staging creation, population, FK validation, swap, and dropping the old tables —
runs in one transaction, so a crash or Ctrl+C at any point rolls back to exactly the previous
state with nothing left behind; a prior incident (see the "no servers" dictionary-lock
investigation) found an orphaned import connection holding the live tables' exclusive lock for
45+ minutes, blocking every dictionary lookup and vocabulary save — this design makes that
class of bug impossible regardless of how the script dies.

kaikki.org has no stable, dated download URL — it overwrites the file on each rebuild. There
is no way to pin an exact version upstream; `--source-version` (default: today's date) records
what we saw at download time, which is the closest available approximation to a pinned version.
The raw downloaded dump is never committed (see .gitignore).
"""

import argparse
import gzip
import json
import time
import urllib.request
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import MetaData, Table, insert, text
from sqlalchemy.orm import Session

from app.core.db import UntimedSessionLocal
from app.models import DictionaryEntry, DictionaryForm, DictionaryTranslation

DEFAULT_SOURCE_URL = "https://kaikki.org/dictionary/downloads/de/de-extract.jsonl.gz"
SOURCE_NAME = "kaikki-de-extract"
# Rows per batched INSERT, not per flush+expunge as in the old row-at-a-time version — large
# enough to amortize round-trip overhead, small enough to keep memory bounded.
BATCH_SIZE = 5000

# Matches dictionary_forms.form's column width. A handful of kaikki entries tag a long
# descriptive note (not an actual inflected word) as a "form" — real surface forms are never
# anywhere close to this long, so these are a source data-quality issue to skip, not word
# forms to accommodate by widening the column.
MAX_FORM_LENGTH = 255

# kaikki tags noun gender as a plain string on the entry's own top-level `tags` list (e.g.
# "tags": ["feminine"] for "Universitaet"), not inside any individual sense's tags - confirmed
# against the real dump, where senses[].tags is null for the vast majority of nouns.
# Normalized here to spaCy's own morph codes so the lookup service and frontend never need a
# second gender vocabulary - see dictionary_entry.py.
GENDER_TAGS = {"masculine": "Masc", "feminine": "Fem", "neuter": "Neut"}

# Only the languages the app can show dictionary meanings in (see
# dictionary_service.dictionary_lang_for) — the dump has hundreds, and most entries'
# translation lists are dominated by languages nobody here reads.
TRANSLATION_LANGS = frozenset({"en", "es"})
MAX_SENSE_INDEX_LENGTH = 32

# The dataset's own marker for inflected-form entries ("Scheine", "ging", "Häuser"): the
# entry-level `tags` and each such sense's `tags` contain "form-of", and the sense carries
# `form_of: [{"word": <base lemma>}]`. Detected from these fields, never by parsing glosses.
FORM_OF_TAG = "form-of"


@dataclass
class ImportStats:
    entries: int = 0
    forms: int = 0
    translations: int = 0
    form_of_entries: int = 0
    entries_with_translations: dict[str, int] = field(
        default_factory=lambda: dict.fromkeys(sorted(TRANSLATION_LANGS), 0)
    )


def _open_source(source: str) -> Iterator[str]:
    """Yields decoded JSONL lines from a local path or a URL, streaming either way."""
    if source.startswith("http://") or source.startswith("https://"):
        with urllib.request.urlopen(source) as response:  # noqa: S310 - fixed source, read-only
            with gzip.GzipFile(fileobj=response) as gz:
                for raw_line in gz:
                    yield raw_line.decode("utf-8")
        return

    path = Path(source)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        yield from handle


def _extract_gender(tags: list[str]) -> str | None:
    for tag in tags:
        normalized = GENDER_TAGS.get(tag)
        if normalized is not None:
            return normalized
    return None


def _is_plural_only(tags: list[str], forms: list[dict]) -> bool:
    """True for genuine plurale-tantum nouns (e.g. "Eltern", "Kosten", "Ferien"): no gender
    tag at all, and every tagged form is plural with none singular - a real noun that simply
    has no singular, not just an entry missing gender data. These still get a nominative
    article ("die") shown in the UI despite having no gender - see schemas/dictionary.py."""
    if _extract_gender(tags) is not None:
        return False
    has_plural_form = False
    for form in forms:
        form_tags = form.get("tags", [])
        if "singular" in form_tags:
            return False
        if "plural" in form_tags:
            has_plural_form = True
    return has_plural_form


def _extract_plural(forms: list[dict]) -> str | None:
    for form in forms:
        if "plural" in form.get("tags", []):
            plural = form.get("form")
            if plural and len(plural) <= MAX_FORM_LENGTH:
                return plural
    return None


def _extract_glosses(senses: list[dict]) -> list[str]:
    glosses: list[str] = []
    for sense in senses:
        glosses.extend(sense.get("glosses", []))
    return glosses


def _extract_form_of_lemma(tags: list[str], senses: list[dict]) -> str | None:
    """The base lemma for a form-of entry, or None for a real (lemma) entry. An entry counts
    as form-of only if the entry itself is tagged so, or every sense is — an entry mixing a
    real sense with a form-of sense keeps its real meaning and stays a lemma entry."""
    sense_is_form_of = [FORM_OF_TAG in (sense.get("tags") or []) for sense in senses]
    if FORM_OF_TAG not in tags and not (sense_is_form_of and all(sense_is_form_of)):
        return None
    for sense in senses:
        for target in sense.get("form_of") or []:
            word = target.get("word")
            if word and len(word) <= MAX_FORM_LENGTH:
                return word
    return None


def _extract_translations(entry_id: uuid.UUID, translations: list[dict]) -> list[dict]:
    rows: list[dict] = []
    seen: set[tuple[str, str, str | None]] = set()
    for position, translation in enumerate(translations):
        lang = translation.get("lang_code")
        word = (translation.get("word") or "").strip()
        if lang not in TRANSLATION_LANGS or not word or len(word) > MAX_FORM_LENGTH:
            continue
        sense_index = translation.get("sense_index") or None
        if sense_index is not None:
            sense_index = str(sense_index)[:MAX_SENSE_INDEX_LENGTH]
        key = (lang, word, sense_index)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "entry_id": entry_id,
                "lang": lang,
                "word": word,
                "sense_index": sense_index,
                "sense_label": translation.get("sense") or None,
                # Capped to SMALLINT; real entries list a few hundred translations at most.
                "position": min(position, 32767),
            }
        )
    return rows


def _staging_table_for(model_table: Table) -> Table:
    """A Table object with the same columns as `model_table` bound to a `_staging` name, so
    Core `insert()` can target the staging table with the exact same param dicts used for the
    live one."""
    return model_table.to_metadata(MetaData(), name=f"{model_table.name}_staging")


def _drop_staging_tables(session: Session) -> None:
    # Children (forms, translations) first — they hold the FKs, if a previous attempt got
    # far enough to add them before failing.
    session.execute(text("DROP TABLE IF EXISTS dictionary_translations_staging"))
    session.execute(text("DROP TABLE IF EXISTS dictionary_forms_staging"))
    session.execute(text("DROP TABLE IF EXISTS dictionary_entries_staging"))


def _create_staging_tables(session: Session) -> None:
    # Defensive, for idempotency: a staging table should never survive a previous run (any
    # failure rolls back the whole transaction, including the CREATE TABLE below), but this
    # makes a from-scratch run safe even if something outside this script's control left one
    # behind.
    _drop_staging_tables(session)
    session.execute(
        text("CREATE TABLE dictionary_entries_staging (LIKE dictionary_entries INCLUDING ALL)")
    )
    session.execute(
        text("CREATE TABLE dictionary_forms_staging (LIKE dictionary_forms INCLUDING ALL)")
    )
    session.execute(
        text(
            "CREATE TABLE dictionary_translations_staging "
            "(LIKE dictionary_translations INCLUDING ALL)"
        )
    )


def _finalize_and_swap_staging_tables(session: Session) -> None:
    """Adds back the one thing `LIKE ... INCLUDING ALL` never copies (foreign keys), which
    also validates every staged form row references a real staged entry — a data-integrity
    problem fails here, before anything goes live — then does the actual swap: rename the
    live tables out of the way, the staging tables into their place, and drop the old ones.
    Renames and drops are metadata-only, so the exclusive lock they need on the live tables is
    held for milliseconds, not the whole import.

    Known, accepted cosmetic limitation: the constraints/indexes `LIKE ... INCLUDING ALL`
    copies get Postgres's auto-generated names (e.g. `dictionary_entries_staging_pkey`), not
    this codebase's `pk_dictionary_entries`/`ix_..._lower` naming convention — they stay named
    that way permanently after the swap, since nothing renames them back. They are fully
    functional (same columns, same uniqueness/FK behavior) under either name; only a future
    `alembic revision --autogenerate` run would show a cosmetic rename-only diff for these two
    tables, safe to absorb into a later migration rather than something this script needs to
    solve.
    """
    session.execute(
        text(
            "ALTER TABLE dictionary_forms_staging "
            "ADD CONSTRAINT fk_dictionary_forms_staging_dictionary_entry_id "
            "FOREIGN KEY (dictionary_entry_id) REFERENCES dictionary_entries_staging (id) "
            "ON DELETE CASCADE"
        )
    )
    session.execute(
        text(
            "ALTER TABLE dictionary_translations_staging "
            "ADD CONSTRAINT fk_dictionary_translations_staging_entry_id "
            "FOREIGN KEY (entry_id) REFERENCES dictionary_entries_staging (id) "
            "ON DELETE CASCADE"
        )
    )
    session.execute(text("ALTER TABLE dictionary_entries RENAME TO dictionary_entries_old"))
    session.execute(text("ALTER TABLE dictionary_forms RENAME TO dictionary_forms_old"))
    session.execute(
        text("ALTER TABLE dictionary_translations RENAME TO dictionary_translations_old")
    )
    session.execute(text("ALTER TABLE dictionary_entries_staging RENAME TO dictionary_entries"))
    session.execute(text("ALTER TABLE dictionary_forms_staging RENAME TO dictionary_forms"))
    session.execute(
        text("ALTER TABLE dictionary_translations_staging RENAME TO dictionary_translations")
    )
    # Children first: they still hold the original FKs pointing at entries_old.
    session.execute(text("DROP TABLE dictionary_forms_old"))
    session.execute(text("DROP TABLE dictionary_translations_old"))
    session.execute(text("DROP TABLE dictionary_entries_old"))


def import_dictionary(
    source: str, source_version: str, db: Session | None = None
) -> tuple[int, int]:
    """Returns (entry_count, form_count) — see import_dictionary_with_stats for the full
    counts."""
    stats = import_dictionary_with_stats(source, source_version, db=db)
    return stats.entries, stats.forms


def import_dictionary_with_stats(
    source: str, source_version: str, db: Session | None = None
) -> ImportStats:
    """Raises and leaves the previous data intact on any
    error or interruption (including Ctrl+C) — nothing commits until the staged data has
    fully replaced the live tables, so the only two possible outcomes are "exactly the
    previous dataset, untouched" or "exactly the new one," never a partial mix.

    `db` is optional so tests can pass the shared `db_session` fixture (savepoint-joined —
    this function's own `commit()` then only closes that savepoint, not the test's outer
    transaction, exactly like every other service function in this codebase); the CLI entry
    point below creates and closes its own session on a separate, untimed engine (see
    app/core/db.py — this import can legitimately run far longer than the app's own
    statement_timeout allows).
    """
    owns_session = db is None
    session = db if db is not None else UntimedSessionLocal()
    stats = ImportStats()
    entry_rows: list[dict] = []
    form_rows: list[dict] = []
    translation_rows: list[dict] = []

    entries_staging = _staging_table_for(DictionaryEntry.__table__)
    forms_staging = _staging_table_for(DictionaryForm.__table__)
    translations_staging = _staging_table_for(DictionaryTranslation.__table__)

    def flush_batches() -> None:
        # Core `insert()` against the Table directly, with a list of param dicts, so
        # psycopg can send one batched (executemany-style) statement instead of this
        # function being called once per row — the ORM's session.add() per row was the
        # actual bottleneck, not I/O or JSON parsing.
        if entry_rows:
            session.execute(insert(entries_staging), entry_rows)
            entry_rows.clear()
        if form_rows:
            session.execute(insert(forms_staging), form_rows)
            form_rows.clear()
        if translation_rows:
            session.execute(insert(translations_staging), translation_rows)
            translation_rows.clear()

    try:
        _create_staging_tables(session)

        for line_number, raw_line in enumerate(_open_source(source), start=1):
            line = raw_line.strip()
            if not line:
                continue
            data = json.loads(line)

            # The source is already pre-filtered to German, but never trust that blindly.
            if data.get("lang_code") != "de":
                continue

            senses = data.get("senses", [])
            glosses = _extract_glosses(senses)
            if not glosses:
                continue

            forms = data.get("forms", [])
            tags = data.get("tags", [])
            entry_id = uuid.uuid4()
            form_of_lemma = _extract_form_of_lemma(tags, senses)
            entry_rows.append(
                {
                    "id": entry_id,
                    "lemma": data["word"],
                    # Kept verbatim - never filtered to an allowlist, so idiom/phrase
                    # entries (pos == "phrase") survive import for phrase lookups.
                    "pos": data.get("pos", ""),
                    "gender": _extract_gender(tags),
                    "plural_only": _is_plural_only(tags, forms),
                    "plural": _extract_plural(forms),
                    "glosses": glosses,
                    "form_of_lemma": form_of_lemma,
                    "source": SOURCE_NAME,
                    "source_version": source_version,
                }
            )
            stats.entries += 1
            if form_of_lemma is not None:
                stats.form_of_entries += 1

            for form in forms:
                form_text = form.get("form")
                if not form_text or len(form_text) > MAX_FORM_LENGTH:
                    continue
                form_rows.append({"dictionary_entry_id": entry_id, "form": form_text})
                stats.forms += 1

            entry_translations = _extract_translations(entry_id, data.get("translations", []))
            translation_rows.extend(entry_translations)
            stats.translations += len(entry_translations)
            for lang in {row["lang"] for row in entry_translations}:
                stats.entries_with_translations[lang] += 1

            if line_number % BATCH_SIZE == 0:
                flush_batches()
                print(
                    f"  ...{line_number} lines read, {stats.entries} entries imported so far",
                    flush=True,
                )

        flush_batches()
        _finalize_and_swap_staging_tables(session)
        session.commit()
        # The planner's row-count estimate for a table is whatever it was the last time
        # someone analyzed it — after a multi-million-row swap that's wildly stale (or, for a
        # table that's never been analyzed, -1/"unknown"), which can be enough to make the
        # planner pick a sequential scan over a perfectly good index. Runs after commit (the
        # live tables are already in place, no lock contention risk) so it never extends the
        # brief rename window above.
        session.execute(text("ANALYZE dictionary_entries"))
        session.execute(text("ANALYZE dictionary_forms"))
        session.execute(text("ANALYZE dictionary_translations"))
        session.commit()
    except BaseException:
        # Covers KeyboardInterrupt too (it isn't an Exception subclass) — whatever stage we
        # were at, rolling back undoes the staging tables along with everything else, since
        # nothing in this function ever commits before this point.
        session.rollback()
        raise
    finally:
        if owns_session:
            session.close()

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        default=DEFAULT_SOURCE_URL,
        help="Local path or URL to the gzip JSONL dump (default: the live kaikki.org URL).",
    )
    parser.add_argument(
        "--source-version",
        default=None,
        help="Version tag to record (e.g. the dump date shown on the download page). "
        "Defaults to today's date.",
    )
    args = parser.parse_args()

    source_version = args.source_version or time.strftime("%Y-%m-%d")

    print(f"Importing from {args.source!r} (source_version={source_version!r})...", flush=True)
    started = time.perf_counter()
    stats = import_dictionary_with_stats(args.source, source_version)
    elapsed = time.perf_counter() - started

    with_translations = ", ".join(
        f"{lang}: {count}" for lang, count in stats.entries_with_translations.items()
    )
    print(
        f"Done: {stats.entries} entries ({stats.form_of_entries} form-of), {stats.forms} forms, "
        f"{stats.translations} translations (entries with translations - {with_translations}), "
        f"{elapsed:.1f}s.",
        flush=True,
    )


if __name__ == "__main__":
    main()
