"""One-off backfill: fixes `gender`/`plural_only` on existing dictionary_entries rows
without a full ~24-minute re-import, now that import_dictionary.py's `_extract_gender`/
`_is_plural_only` read the dump's real top-level `tags` field instead of the wrong
senses[].tags location (see the regression tests added alongside this fix).

    uv run python -m app.scripts.backfill_dictionary_gender [--source PATH_OR_URL]

Streams the same dump the live table was imported from and recomputes gender/plural_only per
noun line exactly like import_dictionary.py does. Matches each dump line to a specific live
row by primary key, not by a (lemma, pos, glosses) WHERE clause: `lemma` only has a
lower(lemma) functional index and `glosses` is JSONB, so an UPDATE filtered on those directly
would force a full sequential scan per statement - against a 1.3M-row table that stalls for
minutes per batch, holding row locks the whole time (the exact "no servers" dictionary-lock
failure mode import_dictionary.py's own staging-table design exists to avoid). Instead, every
live noun row's (id, lemma, glosses) is preloaded into memory up front; each dump line looks
up its candidates by lemma in that in-memory map and matches the one whose glosses are
identical (disambiguating heteronym pairs like "der/die Kiefer", which share lemma and pos but
never glosses), then updates by `id` - the primary key, always index-backed and fast.

Uses the untimed engine with a short, separately-committed transaction per batch (never one
transaction for the whole stream). Safe to re-run: every batch is an idempotent UPDATE to the
same computed values.
"""

import argparse
import json
import time
import uuid

from sqlalchemy import bindparam, func, select, update
from sqlalchemy.orm import Session

from app.core.db import UntimedSessionLocal
from app.models import DictionaryEntry
from app.scripts.import_dictionary import (
    DEFAULT_SOURCE_URL,
    _extract_gender,
    _extract_glosses,
    _is_plural_only,
    _open_source,
)

BATCH_SIZE = 1000


def _noun_gender_coverage(session: Session) -> tuple[int, int]:
    """Returns (nouns_with_gender, total_nouns)."""
    total = session.scalar(
        select(func.count()).select_from(DictionaryEntry).where(DictionaryEntry.pos == "noun")
    )
    with_gender = session.scalar(
        select(func.count())
        .select_from(DictionaryEntry)
        .where(DictionaryEntry.pos == "noun", DictionaryEntry.gender.isnot(None))
    )
    return with_gender, total


def _load_noun_candidates(session: Session) -> dict[str, list[tuple[uuid.UUID, list]]]:
    """{lemma: [(id, glosses), ...]} for every noun row currently live, so dump lines can be
    matched to a specific row by primary key instead of a sequential scan per UPDATE."""
    rows = session.execute(
        select(DictionaryEntry.id, DictionaryEntry.lemma, DictionaryEntry.glosses).where(
            DictionaryEntry.pos == "noun"
        )
    ).all()
    index: dict[str, list[tuple[uuid.UUID, list]]] = {}
    for row_id, lemma, glosses in rows:
        index.setdefault(lemma, []).append((row_id, glosses))
    return index


def backfill(source: str) -> tuple[int, int]:
    """Returns (rows_matched, rows_updated) - usually equal; they can differ only if the
    live dump has since changed upstream and a line no longer matches any live row."""
    session = UntimedSessionLocal()
    table = DictionaryEntry.__table__
    stmt = (
        update(table)
        .where(table.c.id == bindparam("b_id"))
        .values(gender=bindparam("b_gender"), plural_only=bindparam("b_plural_only"))
    )

    print("Loading existing noun entries for id-based matching...", flush=True)
    candidates_by_lemma = _load_noun_candidates(session)
    print(
        f"Loaded {sum(len(v) for v in candidates_by_lemma.values())} live noun entries.",
        flush=True,
    )

    batch: list[dict] = []
    rows_updated = 0
    rows_matched = 0

    def flush() -> None:
        nonlocal rows_updated, batch
        if not batch:
            return
        result = session.execute(stmt, batch)
        rows_updated += result.rowcount
        session.commit()
        batch = []

    try:
        for raw_line in _open_source(source):
            line = raw_line.strip()
            if not line:
                continue
            data = json.loads(line)
            if data.get("lang_code") != "de" or data.get("pos") != "noun":
                continue

            senses = data.get("senses", [])
            glosses = _extract_glosses(senses)
            if not glosses:
                continue

            tags = data.get("tags", [])
            forms = data.get("forms", [])
            gender = _extract_gender(tags)
            plural_only = _is_plural_only(tags, forms)
            if gender is None and not plural_only:
                continue  # matches the column defaults already - nothing to update

            matched_id = next(
                (
                    row_id
                    for row_id, row_glosses in candidates_by_lemma.get(data["word"], [])
                    if row_glosses == glosses
                ),
                None,
            )
            if matched_id is None:
                continue  # no live row corresponds to this dump line anymore

            rows_matched += 1
            batch.append({"b_id": matched_id, "b_gender": gender, "b_plural_only": plural_only})
            if len(batch) >= BATCH_SIZE:
                flush()
                print(f"  ...{rows_matched} rows matched/updated so far", flush=True)
        flush()
    finally:
        session.close()

    return rows_matched, rows_updated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        default=DEFAULT_SOURCE_URL,
        help="Local path or URL to the gzip JSONL dump (default: the live kaikki.org URL).",
    )
    args = parser.parse_args()

    report_session = UntimedSessionLocal()
    before_with_gender, total_nouns = _noun_gender_coverage(report_session)
    report_session.close()
    print(
        f"Before: {before_with_gender}/{total_nouns} noun entries have gender "
        f"({100 * before_with_gender / total_nouns:.2f}%)",
        flush=True,
    )

    started = time.perf_counter()
    rows_matched, rows_updated = backfill(args.source)
    elapsed = time.perf_counter() - started

    report_session = UntimedSessionLocal()
    after_with_gender, total_nouns = _noun_gender_coverage(report_session)
    report_session.close()
    print(
        f"Done in {elapsed:.1f}s: {rows_matched} rows matched, {rows_updated} rows updated.",
        flush=True,
    )
    print(
        f"After: {after_with_gender}/{total_nouns} noun entries have gender "
        f"({100 * after_with_gender / total_nouns:.2f}%)",
        flush=True,
    )


if __name__ == "__main__":
    main()
