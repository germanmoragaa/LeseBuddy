from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class VocabularySaveRequest(BaseModel):
    article_id: UUID
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    # Best-effort: any id here that isn't one of the user's own decks is silently ignored
    # rather than failing the whole save - see deck_service.add_item_to_decks.
    deck_ids: list[UUID] | None = None


class OccurrenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    article_id: UUID
    start_offset: int
    end_offset: int
    context_sentence: str
    created_at: datetime


class VocabularyItemListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lemma: str
    display_form: str
    meaning: str | None
    translation: str | None
    part_of_speech: str
    grammar_metadata: dict
    notes: str | None
    deck_ids: list[UUID]
    created_at: datetime
    updated_at: datetime


class VocabularyItemDetail(VocabularyItemListItem):
    occurrences: list[OccurrenceRead]


class VocabularySaveResponse(BaseModel):
    item: VocabularyItemListItem
    already_saved: bool


class VocabularyListResponse(BaseModel):
    items: list[VocabularyItemListItem]
    total: int
    page: int
    page_size: int


class VocabularyPatchRequest(BaseModel):
    meaning: str | None = None
    translation: str | None = None
    notes: str | None = None


class VocabularyOccurrenceSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    start_offset: int
    end_offset: int
    vocabulary_item_id: UUID
