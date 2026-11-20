from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# Deprecated response fields (meaning, translation, context_sentence) are still dual-written
# and returned until the UI reads only meanings/context_line — see docs/architecture.md's
# follow-up list. `deprecated=True` marks them in the OpenAPI schema.
_DEPRECATED_MEANING = "Deprecated: first dictionary gloss. Use `meanings`."
_DEPRECATED_TRANSLATION = "Deprecated: contextual DeepL translation. Use `meanings`."
_DEPRECATED_CONTEXT_SENTENCE = "Deprecated: same as `context_line`."


class Meaning(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    source: Literal["machine", "dictionary"]
    sense_label: str | None = None


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
    context_sentence: str = Field(description=_DEPRECATED_CONTEXT_SENTENCE, deprecated=True)
    context_line: str | None
    context_translation: str | None
    # True when the line translation failed (or predates it) - retry via
    # POST /api/v1/vocabulary/occurrences/{id}/retry-translation.
    needs_translation: bool
    created_at: datetime


class VocabularyItemListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lemma: str
    display_form: str
    meaning: str | None = Field(description=_DEPRECATED_MEANING, deprecated=True)
    translation: str | None = Field(description=_DEPRECATED_TRANSLATION, deprecated=True)
    meanings: list[Meaning]
    example_occurrence_id: UUID | None
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
    # True when DeepL failed during the save: the word is saved, but its contextual
    # translation and/or line translation are missing and can be retried.
    translation_pending: bool = False
    occurrence_id: UUID | None = None


class VocabularyListResponse(BaseModel):
    items: list[VocabularyItemListItem]
    total: int
    page: int
    page_size: int


class VocabularyPatchRequest(BaseModel):
    meaning: str | None = Field(default=None, description=_DEPRECATED_MEANING, deprecated=True)
    translation: str | None = Field(
        default=None, description=_DEPRECATED_TRANSLATION, deprecated=True
    )
    notes: str | None = None
    # Replaces the whole ordered list (add/remove/reorder happen client-side).
    meanings: list[Meaning] | None = Field(default=None, max_length=50)
    # One of this item's own occurrences, or null to fall back to the first one saved.
    example_occurrence_id: UUID | None = None


class OccurrencePatchRequest(BaseModel):
    context_translation: str | None = Field(default=None, max_length=2000)


class VocabularyOccurrenceSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    start_offset: int
    end_offset: int
    vocabulary_item_id: UUID
