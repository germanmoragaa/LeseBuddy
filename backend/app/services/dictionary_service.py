from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import DictionaryEntry, DictionaryForm
from app.services.selection import ResolvedSelection


def lookup(db: Session, lemma: str, pos: str) -> DictionaryEntry | None:
    """Exact lemma+pos match (case-insensitive), falling back to lemma-only if no row
    matches that exact pos. Returns None — never a guess — if there's no entry at all."""
    exact = db.scalar(
        select(DictionaryEntry).where(
            func.lower(DictionaryEntry.lemma) == lemma.lower(),
            DictionaryEntry.pos == pos,
        )
    )
    if exact is not None:
        return exact
    return db.scalar(
        select(DictionaryEntry).where(func.lower(DictionaryEntry.lemma) == lemma.lower())
    )


def lookup_by_surface_form(db: Session, surface_form: str) -> DictionaryEntry | None:
    """Falls back to the inflected-forms index when the surface form doesn't match any
    lemma directly (e.g. "Bücher" -> the entry for "Buch")."""
    form_row = db.scalar(
        select(DictionaryForm).where(func.lower(DictionaryForm.form) == surface_form.lower())
    )
    if form_row is None:
        return None
    return db.get(DictionaryEntry, form_row.dictionary_entry_id)


def lookup_phrase(db: Session, phrase_text: str) -> DictionaryEntry | None:
    """Exact, case-insensitive match on the full phrase text — no POS filter, no partial
    matching. Returns None if the phrase isn't in the dictionary; never a guess."""
    return db.scalar(
        select(DictionaryEntry).where(func.lower(DictionaryEntry.lemma) == phrase_text.lower())
    )


def resolve_dictionary_entry(db: Session, selection: ResolvedSelection) -> DictionaryEntry | None:
    """Routes a resolved selection to the right lookup strategy: phrase text for multi-word
    selections, the combined lemma for separable verbs, otherwise lemma+pos with an
    inflected-form fallback."""
    if selection.is_phrase:
        return lookup_phrase(db, selection.surface_text)
    if selection.is_separable_verb:
        return lookup(db, selection.lemma, selection.pos)

    entry = lookup(db, selection.lemma, selection.pos)
    if entry is not None:
        return entry
    return lookup_by_surface_form(db, selection.surface_text)
