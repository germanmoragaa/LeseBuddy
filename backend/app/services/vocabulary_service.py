import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Article, ArticleVocabulary, DeckItem, Flashcard, User, VocabularyItem
from app.services.analysis_service import get_or_create_analysis
from app.services.deck_service import add_item_to_decks
from app.services.dictionary_service import dictionary_meanings, resolve_dictionary_entry
from app.services.selection import ResolvedSelection, resolve_selection
from app.services.translation.provider import TranslationProvider
from app.services.translation_service import (
    RETRYABLE_TRANSLATION_ERRORS,
    context_translation_request,
    lookup_cached_translation,
    translate_text,
)

# Mirrors schemas/dictionary.py's GENDER_TO_ARTICLE - kept local rather than imported since a
# service importing a response schema's constant would be an unusual layering direction for
# this codebase; it's a fixed 3-entry mapping, not something that drifts independently.
GENDER_TO_ARTICLE = {"Masc": "der", "Fem": "die", "Neut": "das"}

# `meanings[].source` values.
MACHINE = "machine"
DICTIONARY = "dictionary"


class InvalidExampleOccurrenceError(Exception):
    """PATCH set example_occurrence_id to an occurrence that isn't this item's."""


def derive_article(gender: str | None, plural_only: bool) -> str | None:
    """Nominative article for a grammar_metadata snapshot. Plural-only wins over any merged
    gender value (which may have fallen back to spaCy's detected morph) since the
    dictionary's plural-only flag is a verified lexical fact, not a per-sentence guess."""
    if plural_only:
        return "die"
    if gender:
        return GENDER_TO_ARTICLE.get(gender)
    return None


def merge_meanings(existing: list[dict], new: list[dict]) -> list[dict]:
    """`existing` followed by every item of `new` whose text isn't already there,
    case-insensitively. Order is significant: the first meaning is the one the card
    emphasizes, so nothing already in `existing` is ever moved or dropped."""
    merged = [dict(meaning) for meaning in existing]
    seen = {meaning["text"].strip().casefold() for meaning in merged}
    for meaning in new:
        text = (meaning.get("text") or "").strip()
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        merged.append({**meaning, "text": text})
    return merged


def _try_translate(
    db: Session,
    provider: TranslationProvider | None,
    user: User,
    *,
    source_text: str,
    context: str | None,
) -> str | None:
    """A DeepL translation (through the cache and the per-user rate limit), or None on any
    retryable failure - saving a word must never be blocked by DeepL. Without a provider,
    cache-only."""
    if provider is None:
        return lookup_cached_translation(db, source_text, context, user.translation_language)
    try:
        return translate_text(db, provider, user, source_text=source_text, context=context)
    except RETRYABLE_TRANSLATION_ERRORS:
        # Every one of these is raised before translate_text writes anything (rate limit and
        # quota checks, or the provider call itself), so there's nothing to roll back.
        return None


def _find_item_by_lemma(db: Session, user_id, lemma: str) -> VocabularyItem | None:
    return db.scalar(
        select(VocabularyItem).where(
            VocabularyItem.user_id == user_id,
            func.lower(VocabularyItem.lemma) == lemma.lower(),
        )
    )


def _merge_into_existing(
    db: Session, item: VocabularyItem, *, meanings: list[dict], translation: str | None
) -> VocabularyItem:
    """Re-saving an already-saved word: append the meanings it didn't have yet (never
    reorder or drop the user's list) and fill the deprecated `translation` if missing."""
    current = item.meanings or []
    merged = merge_meanings(current, meanings)
    changed = merged != current
    if changed:
        item.meanings = merged
    if item.translation is None and translation is not None:
        item.translation = translation
        changed = True
    if changed:
        db.commit()
        db.refresh(item)
    return item


def _get_or_create_item(
    db: Session,
    user: User,
    *,
    lemma: str,
    display_form: str,
    part_of_speech: str,
    gender: str | None,
    article: str | None,
    plural: str | None,
    plural_only: bool,
    meaning: str | None,
    translation: str | None,
    meanings: list[dict],
) -> VocabularyItem:
    existing = _find_item_by_lemma(db, user.id, lemma)
    if existing is not None:
        return _merge_into_existing(db, existing, meanings=meanings, translation=translation)

    grammar_metadata = {
        key: value
        for key, value in {
            "gender": gender,
            "article": article,
            "plural": plural,
            "plural_only": plural_only,
        }.items()
        if value
    }

    item = VocabularyItem(
        user_id=user.id,
        lemma=lemma,
        display_form=display_form,
        meaning=meaning,
        translation=translation,
        meanings=meanings,
        part_of_speech=part_of_speech,
        grammar_metadata=grammar_metadata,
    )
    db.add(item)
    db.flush()  # populates item.id (server-generated) so the flashcard FK below can use it
    # Every vocabulary item gets exactly one flashcard, due immediately — see
    # docs/decisions/0005-spaced-repetition.md. Inserted in the same transaction as the item
    # so the two can never exist independently of each other.
    db.add(Flashcard(user_id=user.id, vocabulary_item_id=item.id, due_at=datetime.now(UTC)))
    try:
        db.commit()
    except IntegrityError:
        # A concurrent save of the same lemma won the race — reuse its item (and its
        # flashcard, already created alongside it), mirroring
        # analysis_service.get_or_create_analysis's race handling. The rollback discards both
        # the losing item and its flashcard insert together, since they were one transaction.
        db.rollback()
        existing = _find_item_by_lemma(db, user.id, lemma)
        assert existing is not None
        return _merge_into_existing(db, existing, meanings=meanings, translation=translation)

    db.refresh(item)
    return item


def _find_occurrence(db: Session, article_id, start_offset: int, end_offset: int):
    return db.scalar(
        select(ArticleVocabulary).where(
            ArticleVocabulary.article_id == article_id,
            ArticleVocabulary.start_offset == start_offset,
            ArticleVocabulary.end_offset == end_offset,
        )
    )


def _get_or_create_occurrence(
    db: Session,
    *,
    article_id,
    vocabulary_item_id,
    start_offset: int,
    end_offset: int,
    context_line: str,
    context_translation: str | None,
) -> tuple[ArticleVocabulary, bool]:
    """Returns (occurrence, already_existed). An existing occurrence only gets a missing
    line/translation filled in, never overwritten (the user may have edited it)."""
    existing = _find_occurrence(db, article_id, start_offset, end_offset)
    if existing is not None:
        changed = False
        if existing.context_line is None:
            existing.context_line = context_line
            changed = True
        if existing.context_translation is None and context_translation is not None:
            existing.context_translation = context_translation
            changed = True
        if changed:
            db.commit()
            db.refresh(existing)
        return existing, True

    occurrence = ArticleVocabulary(
        article_id=article_id,
        vocabulary_item_id=vocabulary_item_id,
        start_offset=start_offset,
        end_offset=end_offset,
        # Deprecated column, dual-written with context_line (see docs/architecture.md).
        context_sentence=context_line,
        context_line=context_line,
        context_translation=context_translation,
    )
    db.add(occurrence)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = _find_occurrence(db, article_id, start_offset, end_offset)
        assert existing is not None
        return existing, True

    db.refresh(occurrence)
    return occurrence, False


def save_occurrence(
    db: Session,
    user: User,
    article: Article,
    start: int,
    end: int,
    deck_ids: list[uuid.UUID] | None = None,
    provider: TranslationProvider | None = None,
) -> tuple[VocabularyItem, ArticleVocabulary, bool]:
    """Saves a word/expression to the user's vocabulary from a {start, end} selection.

    Everything is re-derived server-side from the stored analysis — the client sends only
    offsets, never lemma/meaning/translation/grammar data directly (see
    docs/decisions/0004-translations-and-dictionary.md). Snapshots `meanings` (DeepL's
    contextual translation first, then the dictionary's translations in the user's
    language) and the occurrence's context line (lyric line for songs, sentence for texts)
    plus its translation. DeepL goes through the translation cache (usually already warm from
    the word panel) and the per-user rate limit; any DeepL failure saves without the
    translation instead of failing — the occurrence's NULL context_translation is the retry
    flag (see retry_occurrence_translation).

    Returns (item, occurrence, already_saved) where already_saved reflects whether this
    exact occurrence (not just the canonical item) pre-existed. `deck_ids`, when given, adds
    the item to those decks - including when the item already existed.
    """
    analysis = get_or_create_analysis(db, article)
    selection = resolve_selection(analysis, article.original_text, start, end, kind=article.kind)
    context_line = selection.context_text(article.original_text)

    dictionary_entry = resolve_dictionary_entry(db, selection)
    gender = dictionary_entry.gender if dictionary_entry is not None else None
    plural_only = dictionary_entry.plural_only if dictionary_entry is not None else False
    plural = dictionary_entry.plural if dictionary_entry is not None else None
    if gender is None and len(selection.tokens) == 1:
        gender = selection.tokens[0].morph.get("Gender")
    grammar_article = derive_article(gender, plural_only)

    meaning = None
    if dictionary_entry is not None and dictionary_entry.glosses:
        meaning = dictionary_entry.glosses[0]

    translation = _try_translate(
        db, provider, user, source_text=selection.surface_text, context=context_line
    )
    line_source, line_context = context_translation_request(selection, article.original_text)
    context_translation = _try_translate(
        db, provider, user, source_text=line_source, context=line_context
    )
    meanings = merge_meanings(
        [{"text": translation, "source": MACHINE}] if translation else [],
        dictionary_meanings(db, dictionary_entry, user.translation_language),
    )

    item = _get_or_create_item(
        db,
        user,
        lemma=selection.lemma,
        display_form=selection.surface_text,
        part_of_speech=selection.pos,
        gender=gender,
        article=grammar_article,
        plural=plural,
        plural_only=plural_only,
        meaning=meaning,
        translation=translation,
        meanings=meanings,
    )
    occurrence, already_existed = _get_or_create_occurrence(
        db,
        article_id=article.id,
        vocabulary_item_id=item.id,
        start_offset=start,
        end_offset=end,
        context_line=context_line,
        context_translation=context_translation,
    )
    if item.example_occurrence_id is None:
        item.example_occurrence_id = occurrence.id
        db.commit()
        db.refresh(item)

    if deck_ids:
        # `item.decks` (backing the deck_ids response field) hasn't been accessed yet at this
        # point in the request, so it lazy-loads fresh after this commit - no explicit
        # refresh needed to see the memberships just added.
        add_item_to_decks(db, user, item.id, deck_ids)

    return item, occurrence, already_existed


def get_occurrence_for_user(db: Session, user: User, occurrence_id) -> ArticleVocabulary | None:
    return db.scalar(
        select(ArticleVocabulary)
        .join(VocabularyItem, VocabularyItem.id == ArticleVocabulary.vocabulary_item_id)
        .where(ArticleVocabulary.id == occurrence_id, VocabularyItem.user_id == user.id)
    )


def resolve_occurrence_selection(
    db: Session, article: Article, occurrence: ArticleVocabulary
) -> ResolvedSelection:
    analysis = get_or_create_analysis(db, article)
    return resolve_selection(
        analysis,
        article.original_text,
        occurrence.start_offset,
        occurrence.end_offset,
        kind=article.kind,
    )


def retry_occurrence_translation(
    db: Session, provider: TranslationProvider, user: User, occurrence: ArticleVocabulary
) -> ArticleVocabulary:
    """Fills an occurrence's missing context translation (and its item's missing contextual
    machine meaning) after a DeepL failure at save time. Unlike saving, translation errors
    propagate here - the API maps them to the same codes as /translate so the UI can say
    why. A no-op when nothing is missing."""
    item = db.get(VocabularyItem, occurrence.vocabulary_item_id)
    assert item is not None
    has_machine_meaning = any(m.get("source") == MACHINE for m in (item.meanings or []))
    if occurrence.context_translation is not None and has_machine_meaning:
        return occurrence

    article = db.get(Article, occurrence.article_id)
    assert article is not None
    selection = resolve_occurrence_selection(db, article, occurrence)
    context_line = selection.context_text(article.original_text)

    context_translation = occurrence.context_translation
    if context_translation is None:
        line_source, line_context = context_translation_request(selection, article.original_text)
        context_translation = translate_text(
            db, provider, user, source_text=line_source, context=line_context
        )
    word_translation = None
    if not has_machine_meaning:
        word_translation = translate_text(
            db, provider, user, source_text=selection.surface_text, context=context_line
        )

    # translate_text commits on a cache miss, so re-read both rows before writing.
    db.refresh(occurrence)
    db.refresh(item)
    if occurrence.context_line is None:
        occurrence.context_line = context_line
    occurrence.context_translation = context_translation
    if word_translation is not None:
        # The contextual translation always leads; a dictionary meaning with the same text is
        # dropped as the duplicate instead.
        item.meanings = merge_meanings(
            [{"text": word_translation, "source": MACHINE}], item.meanings or []
        )
        if item.translation is None:
            item.translation = word_translation
    db.commit()
    db.refresh(occurrence)
    return occurrence


def list_items_for_user(
    db: Session,
    user: User,
    *,
    search: str | None = None,
    part_of_speech: str | None = None,
    deck_id: uuid.UUID | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[VocabularyItem], int]:
    query = select(VocabularyItem).where(VocabularyItem.user_id == user.id)
    if deck_id is not None:
        query = query.where(
            VocabularyItem.id.in_(
                select(DeckItem.vocabulary_item_id).where(DeckItem.deck_id == deck_id)
            )
        )
    if search:
        pattern = f"%{search.lower()}%"
        query = query.where(
            or_(
                func.lower(VocabularyItem.lemma).like(pattern),
                func.lower(VocabularyItem.display_form).like(pattern),
            )
        )
    if part_of_speech:
        query = query.where(VocabularyItem.part_of_speech == part_of_speech)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(
        query.order_by(VocabularyItem.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(items), total


def get_item_for_user(db: Session, user: User, item_id) -> VocabularyItem | None:
    return db.scalar(
        select(VocabularyItem).where(
            VocabularyItem.id == item_id, VocabularyItem.user_id == user.id
        )
    )


def get_occurrences(db: Session, vocabulary_item_id) -> list[ArticleVocabulary]:
    return list(
        db.scalars(
            select(ArticleVocabulary)
            .where(ArticleVocabulary.vocabulary_item_id == vocabulary_item_id)
            .order_by(ArticleVocabulary.created_at.desc())
        )
    )


def list_occurrences_for_article(db: Session, article_id) -> list[ArticleVocabulary]:
    """Used to highlight words already in the user's vocabulary while reading. Deliberately
    not part of /analysis, which is cached per-article-version independent of any user —
    see docs/decisions/0004-translations-and-dictionary.md."""
    return list(
        db.scalars(select(ArticleVocabulary).where(ArticleVocabulary.article_id == article_id))
    )


def patch_item(db: Session, item: VocabularyItem, updates: dict) -> VocabularyItem:
    """`meanings` is deduplicated (first occurrence wins, so the user's order is kept);
    `example_occurrence_id` must be one of this item's own occurrences, or None to fall back
    to the first one saved."""
    if "meanings" in updates:
        updates["meanings"] = merge_meanings([], updates["meanings"] or [])
    if updates.get("example_occurrence_id") is not None:
        owned = db.scalar(
            select(ArticleVocabulary.id).where(
                ArticleVocabulary.id == updates["example_occurrence_id"],
                ArticleVocabulary.vocabulary_item_id == item.id,
            )
        )
        if owned is None:
            raise InvalidExampleOccurrenceError
    for field, value in updates.items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


def patch_occurrence(
    db: Session, occurrence: ArticleVocabulary, updates: dict
) -> ArticleVocabulary:
    for field, value in updates.items():
        setattr(occurrence, field, value)
    db.commit()
    db.refresh(occurrence)
    return occurrence


def delete_item(db: Session, item: VocabularyItem) -> None:
    db.delete(item)
    db.commit()
