"""Imports German dictionary data into dictionary_entries/dictionary_forms.

    uv run python -m app.scripts.import_dictionary [--source PATH_OR_URL] [--source-version TAG]

Source: kaikki.org's English-Wiktionary German-filtered extract (English glosses, already
pre-filtered to German — see docs/decisions/0004-translations-and-dictionary.md for why this
was chosen over the German-Wiktionary extraction). Streams the gzip JSONL file line by line
(never loads the whole file into memory) and replaces the dictionary tables' content in one
transaction: TRUNCATE, batched Core `INSERT` statements (not one ORM `session.add()` per
row — the per-row ORM overhead made the real ~1.3M-line dump take upwards of 10 hours; batched
`executemany`-style inserts are the fix), a single final commit. Concurrent lookups block for
the duration of the import (TRUNCATE takes an exclusive lock) rather than ever seeing a
partially-imported table; a crash mid-import rolls back to the previous good dataset for free.

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
from pathlib import Path

from sqlalchemy import insert, text
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models import DictionaryEntry, DictionaryForm

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

# kaikki tags gender as a plain string inside senses[].tags (e.g. "masculine"), not as its
# own field. Normalized here to spaCy's own morph codes so the lookup service and frontend
# never need a second gender vocabulary — see dictionary_entry.py.
GENDER_TAGS = {"masculine": "Masc", "feminine": "Fem", "neuter": "Neut"}


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


def _extract_gender(senses: list[dict]) -> str | None:
    for sense in senses:
        for tag in sense.get("tags", []):
            normalized = GENDER_TAGS.get(tag)
            if normalized is not None:
                return normalized
    return None


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


def import_dictionary(
    source: str, source_version: str, db: Session | None = None
) -> tuple[int, int]:
    """Returns (entry_count, form_count). Raises and leaves the previous data intact on any
    error, since nothing commits until the whole file has been processed successfully.

    `db` is optional so tests can pass the shared `db_session` fixture (savepoint-joined —
    this function's own `commit()` then only closes that savepoint, not the test's outer
    transaction, exactly like every other service function in this codebase); the CLI entry
    point below creates and closes its own session.
    """
    owns_session = db is None
    session = db if db is not None else SessionLocal()
    entry_count = 0
    form_count = 0
    entry_rows: list[dict] = []
    form_rows: list[dict] = []

    def flush_batches() -> None:
        # Core `insert()` against the Table directly, with a list of param dicts, so
        # psycopg can send one batched (executemany-style) statement instead of this
        # function being called once per row — the ORM's session.add() per row was the
        # actual bottleneck, not I/O or JSON parsing.
        if entry_rows:
            session.execute(insert(DictionaryEntry.__table__), entry_rows)
            entry_rows.clear()
        if form_rows:
            session.execute(insert(DictionaryForm.__table__), form_rows)
            form_rows.clear()

    try:
        session.execute(text("TRUNCATE dictionary_forms, dictionary_entries"))

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
            entry_id = uuid.uuid4()
            entry_rows.append(
                {
                    "id": entry_id,
                    "lemma": data["word"],
                    # Kept verbatim — never filtered to an allowlist, so idiom/phrase
                    # entries (pos == "phrase") survive import for phrase lookups.
                    "pos": data.get("pos", ""),
                    "gender": _extract_gender(senses),
                    "plural": _extract_plural(forms),
                    "glosses": glosses,
                    "source": SOURCE_NAME,
                    "source_version": source_version,
                }
            )
            entry_count += 1

            for form in forms:
                form_text = form.get("form")
                if not form_text or len(form_text) > MAX_FORM_LENGTH:
                    continue
                form_rows.append({"dictionary_entry_id": entry_id, "form": form_text})
                form_count += 1

            if line_number % BATCH_SIZE == 0:
                flush_batches()
                print(
                    f"  ...{line_number} lines read, {entry_count} entries imported so far",
                    flush=True,
                )

        flush_batches()
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        if owns_session:
            session.close()

    return entry_count, form_count


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
    entry_count, form_count = import_dictionary(args.source, source_version)
    elapsed = time.perf_counter() - started

    print(f"Done: {entry_count} entries, {form_count} forms, {elapsed:.1f}s.", flush=True)


if __name__ == "__main__":
    main()
