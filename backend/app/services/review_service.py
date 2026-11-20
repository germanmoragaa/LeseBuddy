import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models import (
    Article,
    ArticleVocabulary,
    DeckItem,
    Flashcard,
    ReviewLog,
    User,
    VocabularyItem,
)
from app.services.grammar import noun_display
from app.services.scheduler import SCHEDULER_VERSION, CardState, Rating, preview, schedule

NOUN_POS = {"NOUN", "PROPN"}


def _card_state(card: Flashcard) -> CardState:
    return CardState(
        ease_factor=card.ease_factor,
        interval_days=card.interval_days,
        repetitions=card.repetitions,
        lapses=card.lapses,
        due_at=card.due_at,
    )


def card_display(item: VocabularyItem) -> str:
    """The card front's headword: "der Schein, -e" for nouns, the lemma (infinitive) for
    other single words, the expression as written for phrases."""
    if item.part_of_speech == "PHRASE":
        return item.display_form
    if item.part_of_speech not in NOUN_POS:
        return item.lemma
    grammar = item.grammar_metadata or {}
    # Items saved before `plural_only` was snapshotted: derive_article only ever produced
    # "die" without a gender for plural-only nouns.
    plural_only = bool(grammar.get("plural_only")) or (
        grammar.get("article") == "die" and not grammar.get("gender")
    )
    return noun_display(item.lemma, grammar.get("article"), grammar.get("plural"), plural_only)


@dataclass
class CardExampleData:
    occurrence: ArticleVocabulary
    article: Article
    line: str
    highlight: tuple[int, int] | None


def locate_highlight(original_text: str, line: str, start: int, end: int) -> tuple[int, int] | None:
    """Where [start, end) (article offsets) falls inside `line`, found by locating the copy
    of `line` in the article that contains the span - code points, like every offset."""
    if not line:
        return None
    position = original_text.find(line, max(0, end - len(line)))
    if position == -1 or position > start or position + len(line) < end:
        return None
    return start - position, end - position


def load_card_examples(
    db: Session, items: list[VocabularyItem]
) -> tuple[dict[uuid.UUID, CardExampleData], dict[uuid.UUID, str]]:
    """Batched (two queries however many cards there are): each item's card example - its
    chosen example_occurrence_id, else the first occurrence saved - and each item's latest
    context sentence for the deprecated `context_sentence` field."""
    if not items:
        return {}, {}
    occurrences = db.scalars(
        select(ArticleVocabulary)
        .where(ArticleVocabulary.vocabulary_item_id.in_([item.id for item in items]))
        .order_by(ArticleVocabulary.created_at, ArticleVocabulary.id)
    ).all()
    by_item: dict[uuid.UUID, list[ArticleVocabulary]] = {}
    for occurrence in occurrences:
        by_item.setdefault(occurrence.vocabulary_item_id, []).append(occurrence)

    chosen: dict[uuid.UUID, ArticleVocabulary] = {}
    latest_sentences: dict[uuid.UUID, str] = {}
    for item in items:
        item_occurrences = by_item.get(item.id)
        if not item_occurrences:
            continue
        latest_sentences[item.id] = item_occurrences[-1].context_sentence
        chosen[item.id] = next(
            (o for o in item_occurrences if o.id == item.example_occurrence_id),
            item_occurrences[0],
        )

    article_ids = {occurrence.article_id for occurrence in chosen.values()}
    articles = {
        article.id: article
        for article in db.scalars(
            select(Article).options(joinedload(Article.song)).where(Article.id.in_(article_ids))
        ).unique()
    }

    examples: dict[uuid.UUID, CardExampleData] = {}
    for item_id, occurrence in chosen.items():
        article = articles[occurrence.article_id]
        line = occurrence.context_line or occurrence.context_sentence
        examples[item_id] = CardExampleData(
            occurrence=occurrence,
            article=article,
            line=line,
            highlight=locate_highlight(
                article.original_text, line, occurrence.start_offset, occurrence.end_offset
            ),
        )
    return examples, latest_sentences


def _deck_membership_filter(deck_id: uuid.UUID):
    return Flashcard.vocabulary_item_id.in_(
        select(DeckItem.vocabulary_item_id).where(DeckItem.deck_id == deck_id)
    )


def list_due_cards(
    db: Session, user: User, now: datetime, limit: int, deck_id: uuid.UUID | None = None
) -> list[tuple[Flashcard, VocabularyItem, dict[Rating, int]]]:
    query = (
        select(Flashcard, VocabularyItem)
        .join(VocabularyItem, Flashcard.vocabulary_item_id == VocabularyItem.id)
        .where(Flashcard.user_id == user.id, Flashcard.due_at <= now)
    )
    if deck_id is not None:
        query = query.where(_deck_membership_filter(deck_id))
    rows = db.execute(query.order_by(Flashcard.due_at).limit(limit)).all()
    return [(card, item, preview(_card_state(card), now)) for card, item in rows]


def get_summary(
    db: Session, user: User, now: datetime, deck_id: uuid.UUID | None = None
) -> tuple[int, datetime | None, int]:
    filters = [Flashcard.user_id == user.id]
    if deck_id is not None:
        filters.append(_deck_membership_filter(deck_id))

    due_count = (
        db.scalar(
            select(func.count()).select_from(Flashcard).where(Flashcard.due_at <= now, *filters)
        )
        or 0
    )
    total_cards = db.scalar(select(func.count()).select_from(Flashcard).where(*filters)) or 0
    next_due_at = db.scalar(select(func.min(Flashcard.due_at)).where(*filters))
    return due_count, next_due_at, total_cards


def get_flashcard_for_user(db: Session, user: User, flashcard_id: uuid.UUID) -> Flashcard | None:
    return db.scalar(
        select(Flashcard).where(Flashcard.id == flashcard_id, Flashcard.user_id == user.id)
    )


def _find_log_by_client_review_id(db: Session, client_review_id: uuid.UUID) -> ReviewLog | None:
    return db.scalar(select(ReviewLog).where(ReviewLog.client_review_id == client_review_id))


def submit_review(
    db: Session,
    user: User,
    flashcard_id: uuid.UUID,
    rating: Rating,
    now: datetime,
    client_review_id: uuid.UUID | None,
) -> ReviewLog | None:
    """Applies `rating` to the user's flashcard and logs it. Returns None if the card doesn't
    exist or isn't the caller's (the router maps that to 404).

    Idempotent on `client_review_id`: a retried/double-submitted request with the same id
    returns the original log instead of re-applying the scheduler a second time. Checked both
    before locking (the common case) and via the unique constraint + rollback on a genuine
    race (two concurrent requests with the same id) — mirroring
    vocabulary_service._get_or_create_item's select → insert → except IntegrityError → re-select
    pattern.
    """
    if client_review_id is not None:
        existing = _find_log_by_client_review_id(db, client_review_id)
        if existing is not None:
            return existing

    # Locks the row for the rest of this transaction so a concurrent review of the same card
    # can't interleave with this one's read-modify-write of its scheduling state.
    card = db.scalar(
        select(Flashcard)
        .where(Flashcard.id == flashcard_id, Flashcard.user_id == user.id)
        .with_for_update()
    )
    if card is None:
        return None

    item = db.scalar(select(VocabularyItem).where(VocabularyItem.id == card.vocabulary_item_id))
    previous_state = _card_state(card)
    new_state = schedule(previous_state, rating, now)

    card.ease_factor = new_state.ease_factor
    card.interval_days = new_state.interval_days
    card.repetitions = new_state.repetitions
    card.lapses = new_state.lapses
    card.due_at = new_state.due_at
    card.last_reviewed_at = now

    log = ReviewLog(
        user_id=user.id,
        flashcard_id=card.id,
        lemma=item.lemma if item is not None else "",
        rating=rating,
        reviewed_at=now,
        previous_ease_factor=previous_state.ease_factor,
        previous_interval_days=previous_state.interval_days,
        previous_due_at=previous_state.due_at,
        new_ease_factor=new_state.ease_factor,
        new_interval_days=new_state.interval_days,
        new_due_at=new_state.due_at,
        scheduler_version=SCHEDULER_VERSION,
        client_review_id=client_review_id,
    )
    db.add(log)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        assert client_review_id is not None
        existing = _find_log_by_client_review_id(db, client_review_id)
        assert existing is not None
        return existing

    db.refresh(log)
    return log
