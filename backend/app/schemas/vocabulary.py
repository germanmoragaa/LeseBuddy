from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class VocabularySaveRequest(BaseModel):
    article_id: UUID
    start: int = Field(ge=0)
    end: int = Field(gt=0)


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
