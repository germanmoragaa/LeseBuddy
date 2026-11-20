import uuid
from collections.abc import Callable
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_clock, get_current_verified_user
from app.core.db import get_db
from app.models import User, VocabularyItem
from app.schemas.review import (
    CardExample,
    CardSong,
    DueFlashcard,
    DueFlashcardsResponse,
    FlashcardBack,
    FlashcardFront,
    ReviewSubmitRequest,
    ReviewSubmitResponse,
    ReviewSummaryResponse,
)
from app.schemas.vocabulary import Meaning
from app.services.deck_service import get_deck_for_user
from app.services.review_service import (
    CardExampleData,
    card_display,
    get_summary,
    list_due_cards,
    load_card_examples,
    submit_review,
)
from app.services.scheduler import Rating

router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"])


def _front(item: VocabularyItem) -> FlashcardFront:
    gender = item.grammar_metadata.get("gender") if item.part_of_speech == "NOUN" else None
    return FlashcardFront(
        display=card_display(item),
        display_form=item.display_form,
        part_of_speech=item.part_of_speech,
        gender=gender,
    )


def _example(data: CardExampleData | None) -> CardExample | None:
    if data is None:
        return None
    song = data.article.song if data.article.kind == "song" else None
    return CardExample(
        line=data.line,
        translation=data.occurrence.context_translation,
        highlight_start=data.highlight[0] if data.highlight else None,
        highlight_end=data.highlight[1] if data.highlight else None,
        song=CardSong(
            title=song.title,
            artist=song.primary_artist,
            cover_url=song.cover_url,
            cover_thumbnail_url=song.cover_thumbnail_url,
        )
        if song is not None
        else None,
    )


def _back(
    item: VocabularyItem, example: CardExampleData | None, context_sentence: str | None
) -> FlashcardBack:
    return FlashcardBack(
        meanings=[Meaning.model_validate(meaning) for meaning in item.meanings or []],
        example=_example(example),
        translation=item.translation,
        glosses=[item.meaning] if item.meaning else [],
        part_of_speech=item.part_of_speech,
        context_sentence=context_sentence,
    )


@router.get("/due", response_model=DueFlashcardsResponse)
def get_due_cards(
    limit: int = Query(default=20, ge=1, le=100),
    deck_id: uuid.UUID | None = Query(default=None),
    user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
    now_fn: Callable[[], datetime] = Depends(get_clock),
) -> DueFlashcardsResponse:
    if deck_id is not None and get_deck_for_user(db, user, deck_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found")

    now = now_fn()
    due = list_due_cards(db, user, now, limit, deck_id=deck_id)
    examples, latest_sentences = load_card_examples(db, [item for _, item, _ in due])
    return DueFlashcardsResponse(
        items=[
            DueFlashcard(
                id=card.id,
                vocabulary_item_id=item.id,
                due_at=card.due_at,
                front=_front(item),
                back=_back(item, examples.get(item.id), latest_sentences.get(item.id)),
                preview=card_preview,
            )
            for card, item, card_preview in due
        ]
    )


@router.get("/summary", response_model=ReviewSummaryResponse)
def get_review_summary(
    deck_id: uuid.UUID | None = Query(default=None),
    user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
    now_fn: Callable[[], datetime] = Depends(get_clock),
) -> ReviewSummaryResponse:
    if deck_id is not None and get_deck_for_user(db, user, deck_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found")

    due_count, next_due_at, total_cards = get_summary(db, user, now_fn(), deck_id=deck_id)
    return ReviewSummaryResponse(
        due_count=due_count, next_due_at=next_due_at, total_cards=total_cards
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ReviewSubmitResponse)
def submit(
    data: ReviewSubmitRequest,
    user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
    now_fn: Callable[[], datetime] = Depends(get_clock),
) -> ReviewSubmitResponse:
    rating: Rating = data.rating
    log = submit_review(db, user, data.flashcard_id, rating, now_fn(), data.client_review_id)
    if log is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flashcard not found")

    return ReviewSubmitResponse(
        flashcard_id=data.flashcard_id,
        rating=log.rating,
        ease_factor=log.new_ease_factor,
        interval_days=log.new_interval_days,
        due_at=log.new_due_at,
        reviewed_at=log.reviewed_at,
    )
