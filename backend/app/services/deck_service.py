import uuid
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Deck, DeckItem, Flashcard, User, VocabularyItem


class DeckNameTakenError(Exception):
    """Raised when the user already has a deck with this name (case-insensitively)."""


class VocabularyItemsNotOwnedError(Exception):
    """Raised when one or more vocabulary_item_ids don't belong to the user (or don't exist)."""


def _find_deck_by_name(db: Session, user_id: uuid.UUID, name: str) -> Deck | None:
    return db.scalar(
        select(Deck).where(Deck.user_id == user_id, func.lower(Deck.name) == name.lower())
    )


def create_deck(db: Session, user: User, name: str, description: str | None) -> Deck:
    if _find_deck_by_name(db, user.id, name) is not None:
        raise DeckNameTakenError

    deck = Deck(user_id=user.id, name=name, description=description)
    db.add(deck)
    try:
        db.commit()
    except IntegrityError:
        # Pre-check above closes the common case; this catches the rare race where two
        # requests for the same name commit concurrently - mirrors
        # auth_service.register_user's username/email race handling.
        db.rollback()
        raise DeckNameTakenError from None
    db.refresh(deck)
    return deck


def get_deck_for_user(db: Session, user: User, deck_id: uuid.UUID) -> Deck | None:
    return db.scalar(select(Deck).where(Deck.id == deck_id, Deck.user_id == user.id))


def _counts_query(now: datetime):
    due_count_col = func.count(DeckItem.vocabulary_item_id).filter(Flashcard.due_at <= now)
    return (
        select(Deck, func.count(DeckItem.vocabulary_item_id), due_count_col)
        .outerjoin(DeckItem, DeckItem.deck_id == Deck.id)
        .outerjoin(Flashcard, Flashcard.vocabulary_item_id == DeckItem.vocabulary_item_id)
        .group_by(Deck.id)
    )


def list_decks_for_user(db: Session, user: User, now: datetime) -> list[tuple[Deck, int, int]]:
    """One aggregated query (a single LEFT JOIN + GROUP BY) for every deck's total/due
    counts - never N+1 per-deck count queries."""
    rows = db.execute(_counts_query(now).where(Deck.user_id == user.id).order_by(Deck.created_at))
    return [(deck, total, due) for deck, total, due in rows]


def get_deck_with_counts_for_user(
    db: Session, user: User, deck_id: uuid.UUID, now: datetime
) -> tuple[Deck, int, int] | None:
    row = db.execute(_counts_query(now).where(Deck.user_id == user.id, Deck.id == deck_id)).first()
    return tuple(row) if row is not None else None  # type: ignore[return-value]


def update_deck(db: Session, deck: Deck, updates: dict) -> Deck:
    for field, value in updates.items():
        setattr(deck, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DeckNameTakenError from None
    db.refresh(deck)
    return deck


def delete_deck(db: Session, deck: Deck) -> None:
    """Deletes the deck and its memberships only (deck_items cascades) - the underlying
    vocabulary_items and flashcards are never touched, so saved words and their SRS progress
    survive a deck being deleted."""
    db.delete(deck)
    db.commit()


def _not_all_owned(db: Session, user_id: uuid.UUID, vocabulary_item_ids: set[uuid.UUID]) -> bool:
    owned_count = db.scalar(
        select(func.count())
        .select_from(VocabularyItem)
        .where(VocabularyItem.id.in_(vocabulary_item_ids), VocabularyItem.user_id == user_id)
    )
    return owned_count != len(vocabulary_item_ids)


def add_items_to_deck(
    db: Session, user: User, deck: Deck, vocabulary_item_ids: list[uuid.UUID]
) -> None:
    """Bulk, idempotent membership add - re-adding an already-member item is a no-op, not a
    conflict. Raises VocabularyItemsNotOwnedError (mapped to 404) if any id doesn't belong to
    `user` or doesn't exist; this is the dedicated, user-facing "add to deck" action, so unlike
    the vocabulary-save convenience path (see add_item_to_decks below) a bad id here is a real
    error, not something to silently drop."""
    unique_ids = set(vocabulary_item_ids)
    if _not_all_owned(db, user.id, unique_ids):
        raise VocabularyItemsNotOwnedError

    rows = [{"deck_id": deck.id, "vocabulary_item_id": item_id} for item_id in unique_ids]
    stmt = pg_insert(DeckItem.__table__).values(rows)
    stmt = stmt.on_conflict_do_nothing(index_elements=["deck_id", "vocabulary_item_id"])
    db.execute(stmt)
    db.commit()


def add_item_to_decks(
    db: Session, user: User, vocabulary_item_id: uuid.UUID, deck_ids: list[uuid.UUID]
) -> None:
    """Adds one vocabulary item to multiple decks at once - used by vocabulary save's optional
    deck_ids. Silently ignores any deck_id that doesn't belong to `user`, since this is a
    best-effort side effect of saving a word, not a dedicated action the way
    POST /decks/{id}/items is (which 404s on an unowned id instead)."""
    unique_deck_ids = set(deck_ids)
    if not unique_deck_ids:
        return
    owned_deck_ids = set(
        db.scalars(
            select(Deck.id).where(Deck.id.in_(unique_deck_ids), Deck.user_id == user.id)
        ).all()
    )
    if not owned_deck_ids:
        return

    rows = [
        {"deck_id": deck_id, "vocabulary_item_id": vocabulary_item_id} for deck_id in owned_deck_ids
    ]
    stmt = pg_insert(DeckItem.__table__).values(rows)
    stmt = stmt.on_conflict_do_nothing(index_elements=["deck_id", "vocabulary_item_id"])
    db.execute(stmt)
    db.commit()


def remove_item_from_deck(db: Session, deck: Deck, vocabulary_item_id: uuid.UUID) -> None:
    """Idempotent: removing a non-member is a silent no-op, matching DELETE's usual semantics
    elsewhere in this codebase rather than 404ing on "already not there"."""
    db.execute(
        delete(DeckItem).where(
            DeckItem.deck_id == deck.id, DeckItem.vocabulary_item_id == vocabulary_item_id
        )
    )
    db.commit()
