"""One-off, idempotent backfill: fills in gender/article inside existing vocabulary_items'
grammar_metadata JSON for nouns, now that dictionary_entries' gender coverage has been
corrected (see backfill_dictionary_gender.py) - items saved before that fix snapshotted
whatever (near-always-null) gender the dictionary had at the time, and that snapshot never
updates itself later (see vocabulary_item.py's docstring - it's a deliberate point-in-time
copy, not a live join).

    uv run python -m app.scripts.backfill_vocabulary_grammar_metadata

Only ever fills in a missing "gender"/"article" key from what the dictionary resolves today;
never overwrites a value an item's grammar_metadata already has (including a spaCy-detected
gender saved as a fallback at the time). Re-running makes no further changes once every
resolvable item already has both keys.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import UntimedSessionLocal
from app.models import VocabularyItem
from app.services import dictionary_service
from app.services.vocabulary_service import derive_article

COMMIT_EVERY = 500

# spaCy's own UPOS tags for nouns (see selection.py) - the only part_of_speech values that
# can plausibly have a gender/article at all.
NOUN_POS_VALUES = ("NOUN", "PROPN")


def backfill(session: Session) -> tuple[int, int]:
    """Returns (items_checked, items_updated)."""
    items = session.scalars(
        select(VocabularyItem).where(VocabularyItem.part_of_speech.in_(NOUN_POS_VALUES))
    ).all()

    items_checked = 0
    items_updated = 0
    for item in items:
        items_checked += 1
        if item.grammar_metadata.get("gender") and item.grammar_metadata.get("article"):
            continue

        entry = dictionary_service.lookup(session, item.lemma, item.part_of_speech)
        if entry is None:
            continue

        gender = item.grammar_metadata.get("gender") or entry.gender
        article = item.grammar_metadata.get("article") or derive_article(gender, entry.plural_only)

        updated_metadata = dict(item.grammar_metadata)
        if gender:
            updated_metadata["gender"] = gender
        if article:
            updated_metadata["article"] = article
        if updated_metadata == item.grammar_metadata:
            continue

        item.grammar_metadata = updated_metadata
        items_updated += 1
        if items_updated % COMMIT_EVERY == 0:
            session.commit()

    session.commit()
    return items_checked, items_updated


def main() -> None:
    session = UntimedSessionLocal()
    try:
        items_checked, items_updated = backfill(session)
    finally:
        session.close()
    print(f"Checked {items_checked} noun vocabulary items, updated {items_updated}.")


if __name__ == "__main__":
    main()
