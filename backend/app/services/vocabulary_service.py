from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Article, ArticleVocabulary, User, VocabularyItem
from app.services.analysis_service import get_or_create_analysis
from app.services.dictionary_service import resolve_dictionary_entry
from app.services.selection import resolve_selection
from app.services.translation_service import lookup_cached_translation


def _find_item_by_lemma(db: Session, user_id, lemma: str) -> VocabularyItem | None:
    return db.scalar(
        select(VocabularyItem).where(
            VocabularyItem.user_id == user_id,
            func.lower(VocabularyItem.lemma) == lemma.lower(),
        )
    )


def _get_or_create_item(
    db: Session,
    user: User,
    *,
    lemma: str,
    display_form: str,
    part_of_speech: str,
    gender: str | None,
    plural: str | None,
    meaning: str | None,
    translation: str | None,
) -> VocabularyItem:
    existing = _find_item_by_lemma(db, user.id, lemma)
    if existing is not None:
        return existing

    grammar_metadata = {
        key: value for key, value in {"gender": gender, "plural": plural}.items() if value
    }

    item = VocabularyItem(
        user_id=user.id,
        lemma=lemma,
        display_form=display_form,
        meaning=meaning,
        translation=translation,
        part_of_speech=part_of_speech,
        grammar_metadata=grammar_metadata,
    )
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        # A concurrent save of the same lemma won the race — reuse its item, mirroring
        # analysis_service.get_or_create_analysis's race handling.
        db.rollback()
        existing = _find_item_by_lemma(db, user.id, lemma)
        assert existing is not None
        return existing

    db.refresh(item)
    return item


def _get_or_create_occurrence(
    db: Session,
    *,
    article_id,
    vocabulary_item_id,
    start_offset: int,
    end_offset: int,
    context_sentence: str,
) -> tuple[ArticleVocabulary, bool]:
    """Returns (occurrence, already_existed)."""
    existing = db.scalar(
        select(ArticleVocabulary).where(
            ArticleVocabulary.article_id == article_id,
            ArticleVocabulary.start_offset == start_offset,
            ArticleVocabulary.end_offset == end_offset,
        )
    )
    if existing is not None:
        return existing, True

    occurrence = ArticleVocabulary(
        article_id=article_id,
        vocabulary_item_id=vocabulary_item_id,
        start_offset=start_offset,
        end_offset=end_offset,
        context_sentence=context_sentence,
    )
    db.add(occurrence)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(ArticleVocabulary).where(
                ArticleVocabulary.article_id == article_id,
                ArticleVocabulary.start_offset == start_offset,
                ArticleVocabulary.end_offset == end_offset,
            )
        )
        assert existing is not None
        return existing, True

    db.refresh(occurrence)
    return occurrence, False


def save_occurrence(
    db: Session, user: User, article: Article, start: int, end: int
) -> tuple[VocabularyItem, bool]:
    """Saves a word/expression to the user's vocabulary from a {start, end} selection.

    Everything is re-derived server-side from the stored analysis — the client sends only
    offsets, never lemma/meaning/translation/grammar data directly (see
    docs/decisions/0004-translations-and-dictionary.md). Reuses whatever's already in
    translation_cache for this exact selection+context+language; never triggers a fresh
    billed DeepL call at save time. Returns (item, already_saved) where already_saved
    reflects whether this exact occurrence (not just the canonical item) pre-existed.
    """
    analysis = get_or_create_analysis(db, article)
    selection = resolve_selection(analysis, article.original_text, start, end)
    context_sentence = article.original_text[selection.sentence.start : selection.sentence.end]

    dictionary_entry = resolve_dictionary_entry(db, selection)
    gender = dictionary_entry.gender if dictionary_entry is not None else None
    plural = dictionary_entry.plural if dictionary_entry is not None else None
    if gender is None and len(selection.tokens) == 1:
        gender = selection.tokens[0].morph.get("Gender")

    meaning = None
    if dictionary_entry is not None and dictionary_entry.glosses:
        meaning = dictionary_entry.glosses[0]

    translation = lookup_cached_translation(
        db, selection.surface_text, context_sentence, user.translation_language
    )

    item = _get_or_create_item(
        db,
        user,
        lemma=selection.lemma,
        display_form=selection.surface_text,
        part_of_speech=selection.pos,
        gender=gender,
        plural=plural,
        meaning=meaning,
        translation=translation,
    )
    _, already_existed = _get_or_create_occurrence(
        db,
        article_id=article.id,
        vocabulary_item_id=item.id,
        start_offset=start,
        end_offset=end,
        context_sentence=context_sentence,
    )

    return item, already_existed


def list_items_for_user(
    db: Session,
    user: User,
    *,
    search: str | None = None,
    part_of_speech: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[VocabularyItem], int]:
    query = select(VocabularyItem).where(VocabularyItem.user_id == user.id)
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
    for field, value in updates.items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


def delete_item(db: Session, item: VocabularyItem) -> None:
    db.delete(item)
    db.commit()
