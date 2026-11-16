import uuid
from collections.abc import Callable
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_clock, get_current_verified_user
from app.core.db import get_db
from app.models import Deck, User
from app.schemas.deck import (
    DeckCreateRequest,
    DeckItemsAddRequest,
    DeckListItem,
    DeckListResponse,
    DeckRead,
    DeckUpdateRequest,
)
from app.services.deck_service import (
    DeckNameTakenError,
    VocabularyItemsNotOwnedError,
    add_items_to_deck,
    create_deck,
    delete_deck,
    get_deck_for_user,
    get_deck_with_counts_for_user,
    list_decks_for_user,
    remove_item_from_deck,
    update_deck,
)

router = APIRouter(prefix="/api/v1/decks", tags=["decks"])


def _name_conflict() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=[
            {
                "loc": ["body", "name"],
                "msg": "A deck with this name already exists.",
                "type": "value_error.conflict",
            }
        ],
    )


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found")


def _to_list_item(deck: Deck, total_count: int, due_count: int) -> DeckListItem:
    return DeckListItem(
        **DeckRead.model_validate(deck).model_dump(), total_count=total_count, due_count=due_count
    )


def _get_or_404(db: Session, user: User, deck_id: uuid.UUID) -> Deck:
    deck = get_deck_for_user(db, user, deck_id)
    if deck is None:
        raise _not_found()
    return deck


@router.post("", status_code=status.HTTP_201_CREATED, response_model=DeckListItem)
def create(
    data: DeckCreateRequest,
    user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
) -> DeckListItem:
    try:
        deck = create_deck(db, user, data.name, data.description)
    except DeckNameTakenError:
        raise _name_conflict() from None
    return _to_list_item(deck, total_count=0, due_count=0)


@router.get("", response_model=DeckListResponse)
def list_decks(
    user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
    now_fn: Callable[[], datetime] = Depends(get_clock),
) -> DeckListResponse:
    rows = list_decks_for_user(db, user, now_fn())
    return DeckListResponse(items=[_to_list_item(deck, total, due) for deck, total, due in rows])


@router.get("/{deck_id}", response_model=DeckListItem)
def get_deck(
    deck_id: uuid.UUID,
    user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
    now_fn: Callable[[], datetime] = Depends(get_clock),
) -> DeckListItem:
    result = get_deck_with_counts_for_user(db, user, deck_id, now_fn())
    if result is None:
        raise _not_found()
    deck, total, due = result
    return _to_list_item(deck, total, due)


@router.patch("/{deck_id}", response_model=DeckRead)
def patch_deck(
    deck_id: uuid.UUID,
    data: DeckUpdateRequest,
    user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
) -> DeckRead:
    deck = _get_or_404(db, user, deck_id)
    try:
        updated = update_deck(db, deck, data.model_dump(exclude_unset=True))
    except DeckNameTakenError:
        raise _name_conflict() from None
    return DeckRead.model_validate(updated)


@router.delete("/{deck_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    deck_id: uuid.UUID,
    user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
) -> None:
    deck = _get_or_404(db, user, deck_id)
    delete_deck(db, deck)


@router.post("/{deck_id}/items", status_code=status.HTTP_204_NO_CONTENT)
def add_items(
    deck_id: uuid.UUID,
    data: DeckItemsAddRequest,
    user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
) -> None:
    deck = _get_or_404(db, user, deck_id)
    try:
        add_items_to_deck(db, user, deck, data.vocabulary_item_ids)
    except VocabularyItemsNotOwnedError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vocabulary item not found"
        ) from None


@router.delete("/{deck_id}/items/{vocabulary_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_item(
    deck_id: uuid.UUID,
    vocabulary_item_id: uuid.UUID,
    user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
) -> None:
    deck = _get_or_404(db, user, deck_id)
    remove_item_from_deck(db, deck, vocabulary_item_id)
