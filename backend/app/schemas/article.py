from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ARTICLE_TEXT_MAX_LENGTH = 50_000


class ArticleCreate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    source_url: str | None = Field(default=None, max_length=2048)
    original_text: str = Field(min_length=1, max_length=ARTICLE_TEXT_MAX_LENGTH)
    language: str = Field(default="de", max_length=8)


class ArticleListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str | None
    source_url: str | None
    language: str
    created_at: datetime
    updated_at: datetime


class ArticleRead(ArticleListItem):
    original_text: str
