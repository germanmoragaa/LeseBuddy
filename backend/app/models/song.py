import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, DateTime, ForeignKeyConstraint, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.article import Article


class Song(TimestampMixin, Base):
    """Song metadata for an article whose `kind` is "song" — strictly 1:1 with `articles`.

    The lyrics themselves live in `articles.original_text` (pasted by the user, never fetched
    from a third party); this row only holds the metadata Genius' official API returns, or a
    manually entered title/artist for songs Genius doesn't have. See
    docs/decisions/0006-songs-and-lyrics.md.

    `user_id` is denormalized from the article and enforced by the composite FK
    (article_id, user_id) -> articles (id, user_id): a song can never belong to a different
    user than its article, and it lets the per-user Genius-id uniqueness live in a plain
    index instead of a join.
    """

    __tablename__ = "songs"

    article_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    # Null for songs saved manually because they aren't on Genius.
    genius_song_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    primary_artist: Mapped[str] = mapped_column(String(255), nullable=False)
    album: Mapped[str | None] = mapped_column(String(255), nullable=True)
    release_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Genius sometimes only knows a year or a display string ("2019", "Summer 1998") rather
    # than a full date, so the display form is kept separately from the typed date.
    release_date_display: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Hotlinked from Genius, never downloaded to our server.
    cover_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    genius_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    metadata_fetched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    article: Mapped["Article"] = relationship(back_populates="song")

    __table_args__ = (
        ForeignKeyConstraint(
            ["article_id", "user_id"],
            ["articles.id", "articles.user_id"],
            ondelete="CASCADE",
        ),
        # The same user can't save the same Genius song twice; songs without a Genius id
        # (manual entries) are deliberately unrestricted.
        Index(
            "ix_songs_user_id_genius_song_id",
            "user_id",
            "genius_song_id",
            unique=True,
            postgresql_where=genius_song_id.is_not(None),
        ),
    )
