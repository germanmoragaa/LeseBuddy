from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.services.scheduler import Rating


class FlashcardFront(BaseModel):
    display_form: str
    part_of_speech: str
    # Only populated for nouns — the frontend renders it as the der/die/das article.
    gender: str | None


class FlashcardBack(BaseModel):
    translation: str | None
    glosses: list[str]
    part_of_speech: str
    context_sentence: str | None


class DueFlashcard(BaseModel):
    id: UUID
    vocabulary_item_id: UUID
    due_at: datetime
    front: FlashcardFront
    back: FlashcardBack
    preview: dict[Rating, int]


class DueFlashcardsResponse(BaseModel):
    items: list[DueFlashcard]


class ReviewSummaryResponse(BaseModel):
    due_count: int
    next_due_at: datetime | None
    total_cards: int


class ReviewSubmitRequest(BaseModel):
    flashcard_id: UUID
    rating: Rating
    client_review_id: UUID | None = None


class ReviewSubmitResponse(BaseModel):
    # Mirrors exactly what review_logs stores, so a replayed idempotent submission (same
    # client_review_id) returns data that was true at the time of that review, not whatever
    # the card's state happens to be now if a later review has since moved it on.
    flashcard_id: UUID
    rating: Rating
    ease_factor: float
    interval_days: int
    due_at: datetime
    reviewed_at: datetime
