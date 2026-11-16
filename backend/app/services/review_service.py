import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import ArticleVocabulary, DeckItem, Flashcard, ReviewLog, User, VocabularyItem
from app.services.scheduler import SCHEDULER_VERSION, CardState, Rating, preview, schedule


def _card_state(card: Flashcard) -> CardState:
    return CardState(
        ease_factor=card.ease_factor,
        interval_days=card.interval_days,
        repetitions=card.repetitions,
        lapses=card.lapses,
        due_at=card.due_at,
    )


def _latest_context_sentence(db: Session, vocabulary_item_id: uuid.UUID) -> str | None:
    occurrence = db.scalar(
        select(ArticleVocabulary)
        .where(ArticleVocabulary.vocabulary_item_id == vocabulary_item_id)
        .order_by(ArticleVocabulary.created_at.desc())
        .limit(1)
    )
    return occurrence.context_sentence if occurrence is not None else None


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


def get_context_sentence(db: Session, vocabulary_item_id: uuid.UUID) -> str | None:
    return _latest_context_sentence(db, vocabulary_item_id)


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
