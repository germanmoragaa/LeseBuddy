from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _non_empty_stripped(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("Deck name cannot be empty.")
    return stripped


class DeckCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    description: str | None = Field(default=None, max_length=200)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _non_empty_stripped(value)


class DeckUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=60)
    description: str | None = Field(default=None, max_length=200)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        return _non_empty_stripped(value) if value is not None else value


class DeckRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class DeckListItem(DeckRead):
    total_count: int
    due_count: int


class DeckListResponse(BaseModel):
    items: list[DeckListItem]


class DeckItemsAddRequest(BaseModel):
    vocabulary_item_ids: list[UUID] = Field(min_length=1)
