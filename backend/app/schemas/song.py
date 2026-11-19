from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.article import ARTICLE_TEXT_MAX_LENGTH


class SongSearchResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    genius_id: int
    title: str
    primary_artist: str
    thumbnail_url: str | None
    cover_url: str | None
    genius_url: str | None
    release_date_display: str | None
    release_year: int | None
    language: str | None


class SongSearchResponse(BaseModel):
    query: str
    results: list[SongSearchResultRead]


class GeniusSongRead(BaseModel):
    """Full metadata for one Genius song — never lyrics (ADR 0006)."""

    model_config = ConfigDict(from_attributes=True)

    genius_id: int
    title: str
    primary_artist: str
    album: str | None
    release_date: date | None
    release_date_display: str | None
    cover_url: str | None
    genius_url: str | None
    language: str | None


class SongCreate(BaseModel):
    """Only the Genius id and the user's own pasted lyrics — all metadata is re-fetched
    server-side (ADR 0006)."""

    genius_song_id: int = Field(gt=0)
    lyrics_text: str = Field(min_length=1, max_length=ARTICLE_TEXT_MAX_LENGTH)

    @field_validator("lyrics_text")
    @classmethod
    def lyrics_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("lyrics_text must not be blank")
        return value
