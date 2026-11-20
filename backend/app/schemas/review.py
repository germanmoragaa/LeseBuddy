from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.vocabulary import Meaning
from app.services.scheduler import Rating


class FlashcardFront(BaseModel):
    # Dictionary-style headword: "der Schein, -e" for nouns (article + plural notation), the
    # infinitive for verbs, the expression itself for phrases.
    display: str
    display_form: str = Field(description="Deprecated: use `display`.", deprecated=True)
    part_of_speech: str
    # Only populated for nouns — the frontend renders it as the der/die/das article.
    gender: str | None


class CardSong(BaseModel):
    title: str
    artist: str
    cover_url: str | None
    cover_thumbnail_url: str | None = None


class CardExample(BaseModel):
    line: str
    translation: str | None
    # Code-point offsets of the saved word within `line` (None if it can't be located).
    highlight_start: int | None
    highlight_end: int | None
    song: CardSong | None


class FlashcardBack(BaseModel):
    # All meanings, in order (the contextual machine translation first).
    meanings: list[Meaning]
    example: CardExample | None
    translation: str | None = Field(description="Deprecated: use `meanings`.", deprecated=True)
    glosses: list[str] = Field(description="Deprecated: use `meanings`.", deprecated=True)
    part_of_speech: str
    context_sentence: str | None = Field(
        description="Deprecated: use `example.line`.", deprecated=True
    )


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
