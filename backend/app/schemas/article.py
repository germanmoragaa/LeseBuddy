from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.article import ArticleKind

ARTICLE_TEXT_MAX_LENGTH = 50_000


class ArticleCreate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    source_url: str | None = Field(default=None, max_length=2048)
    original_text: str = Field(min_length=1, max_length=ARTICLE_TEXT_MAX_LENGTH)
    language: str = Field(default="de", max_length=8)


class SongMetadataRead(BaseModel):
    """Song metadata shown alongside a "song" article. genius_song_id and
    metadata_fetched_at are internal and deliberately not exposed."""

    model_config = ConfigDict(from_attributes=True)

    title: str
    primary_artist: str
    album: str | None
    release_date: date | None
    release_date_display: str | None
    cover_url: str | None
    genius_url: str | None


class ArticleListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kind: ArticleKind
    title: str | None
    source_url: str | None
    language: str
    created_at: datetime
    updated_at: datetime
    word_count: int
    excerpt: str | None
    last_opened_at: datetime | None
    progress_percent: float | None
    # Null unless kind == "song".
    song: SongMetadataRead | None


class ArticleRead(ArticleListItem):
    original_text: str
    reading_position: int | None


class ArticleListResponse(BaseModel):
    items: list[ArticleListItem]
    total: int
    page: int
    page_size: int


class ArticleUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class ArticlePositionUpdate(BaseModel):
    offset: int = Field(ge=0)
