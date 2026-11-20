import re

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models import DictionaryEntry, DictionaryForm, DictionaryTranslation
from app.services.selection import ResolvedSelection

# spaCy UPOS tag -> the dataset's own `pos` values (kaikki's German-Wiktionary extract), in
# preference order. A UPOS with no equivalent (X, SYM, PUNCT, SPACE...) is absent on purpose:
# its lookup falls back to lemma-only rather than guessing a POS.
UPOS_TO_DATASET_POS: dict[str, tuple[str, ...]] = {
    "NOUN": ("noun",),
    "PROPN": ("name", "noun"),
    "VERB": ("verb",),
    "AUX": ("verb",),
    "ADJ": ("adj",),
    "ADV": ("adv",),
    "ADP": ("prep", "postp"),
    "PRON": ("pron",),
    "DET": ("det",),
    "NUM": ("num",),
    "CCONJ": ("conj",),
    "SCONJ": ("conj",),
    "PART": ("particle",),
    "INTJ": ("intj",),
}

# The user's DeepL target language (e.g. "EN-US", "ES") -> the dictionary_translations.lang
# code imported for it. Languages the import doesn't keep get no dictionary meanings.
_DICTIONARY_LANGS = {"EN": "en", "ES": "es"}


def dataset_pos_for(pos: str) -> tuple[str, ...]:
    """Dataset POS candidates for a spaCy UPOS tag. A value that's already lowercase is
    treated as a dataset POS itself (callers and tests that pass "noun" directly)."""
    if pos in UPOS_TO_DATASET_POS:
        return UPOS_TO_DATASET_POS[pos]
    if pos and pos.islower():
        return (pos,)
    return ()


def dictionary_lang_for(translation_language: str) -> str | None:
    return _DICTIONARY_LANGS.get(translation_language.split("-")[0].upper())


def _lemma_entries(lemma: str) -> Select:
    """Real (lemma) entries only: form-of entries ("Scheine" = plural of "Schein") are never
    a lookup result themselves - see lookup_by_surface_form for how they're resolved."""
    return (
        select(DictionaryEntry)
        .where(
            func.lower(DictionaryEntry.lemma) == lemma.lower(),
            DictionaryEntry.form_of_lemma.is_(None),
        )
        # Deterministic among heteronyms; an exact-case match ("Schein" vs "schein") first.
        .order_by((DictionaryEntry.lemma != lemma), DictionaryEntry.id)
        .limit(1)
    )


def lookup(db: Session, lemma: str, pos: str) -> DictionaryEntry | None:
    """Exact lemma + matching POS among non-form-of entries, then the same lemma with any POS
    (still non-form-of). Returns None - never a guess - if neither matches."""
    for dataset_pos in dataset_pos_for(pos):
        exact = db.scalar(_lemma_entries(lemma).where(DictionaryEntry.pos == dataset_pos))
        if exact is not None:
            return exact
    return db.scalar(_lemma_entries(lemma))


def lookup_by_surface_form(
    db: Session, surface_form: str, pos: str | None = None
) -> DictionaryEntry | None:
    """Last-resort fallback when the lemma matched nothing: first the inflected-forms index
    of real entries (e.g. "Bücher" -> "Buch"), then form-of entries spelled like the surface
    form, resolved to their base lemma (e.g. "ging" -> "gehen"). Entries whose POS matches
    `pos` are preferred in both steps."""
    pos_candidates = dataset_pos_for(pos) if pos else ()
    pos_rank = DictionaryEntry.pos.notin_(pos_candidates) if pos_candidates else None

    by_form = (
        select(DictionaryEntry)
        .join(DictionaryForm, DictionaryForm.dictionary_entry_id == DictionaryEntry.id)
        .where(
            func.lower(DictionaryForm.form) == surface_form.lower(),
            DictionaryEntry.form_of_lemma.is_(None),
        )
    )
    if pos_rank is not None:
        by_form = by_form.order_by(pos_rank)
    entry = db.scalar(by_form.order_by(DictionaryEntry.id).limit(1))
    if entry is not None:
        return entry

    form_of = select(DictionaryEntry).where(
        func.lower(DictionaryEntry.lemma) == surface_form.lower(),
        DictionaryEntry.form_of_lemma.is_not(None),
    )
    if pos_rank is not None:
        form_of = form_of.order_by(pos_rank)
    for form_of_entry in db.scalars(form_of.order_by(DictionaryEntry.id)):
        base = lookup(db, form_of_entry.form_of_lemma, form_of_entry.pos)
        if base is not None:
            return base
    return None


def lookup_phrase(db: Session, phrase_text: str) -> DictionaryEntry | None:
    """Exact, case-insensitive match on the full phrase text - no POS filter, no partial
    matching. Returns None if the phrase isn't in the dictionary; never a guess."""
    return db.scalar(_lemma_entries(phrase_text))


def resolve_dictionary_entry(db: Session, selection: ResolvedSelection) -> DictionaryEntry | None:
    """Routes a resolved selection to the right lookup strategy: phrase text for multi-word
    selections, the combined lemma for separable verbs, otherwise lemma+pos with the
    surface-form fallback used only when the lemma matched nothing."""
    if selection.is_phrase:
        return lookup_phrase(db, selection.surface_text)
    if selection.is_separable_verb:
        return lookup(db, selection.lemma, selection.pos)

    entry = lookup(db, selection.lemma, selection.pos)
    if entry is not None:
        return entry
    return lookup_by_surface_form(db, selection.surface_text, selection.pos)


def _sense_sort_key(sense_index: str | None) -> tuple[int, str]:
    match = re.match(r"\d+", sense_index or "")
    return (int(match.group()) if match else 10_000, sense_index or "")


def get_translations(db: Session, entry: DictionaryEntry, lang: str) -> list[DictionaryTranslation]:
    """The entry's translations into `lang`, by sense (1, 2, ... 10) and then in the source's
    own order within a sense."""
    rows = db.scalars(
        select(DictionaryTranslation).where(
            DictionaryTranslation.entry_id == entry.id, DictionaryTranslation.lang == lang
        )
    ).all()
    return sorted(rows, key=lambda row: (_sense_sort_key(row.sense_index), row.position))


def dictionary_meanings(
    db: Session, entry: DictionaryEntry | None, translation_language: str
) -> list[dict]:
    """Dictionary translations as `meanings` items ({text, source, sense_label?}), not yet
    deduplicated - vocabulary_service.merge_meanings does that."""
    lang = dictionary_lang_for(translation_language)
    if entry is None or lang is None:
        return []
    meanings = []
    for row in get_translations(db, entry, lang):
        meaning = {"text": row.word, "source": "dictionary"}
        if row.sense_label:
            meaning["sense_label"] = row.sense_label
        meanings.append(meaning)
    return meanings
