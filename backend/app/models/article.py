import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Literal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.song import Song

ArticleKind = Literal["text", "song"]


class Article(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "articles"
    __table_args__ = (
        Index("ix_articles_user_id_last_opened_at", "user_id", "last_opened_at"),
        CheckConstraint("kind IN ('text', 'song')", name="kind"),
        # Redundant as a uniqueness rule (id alone is the PK) — exists only so songs can
        # reference (id, user_id) with a composite FK. See Song's docstring.
        UniqueConstraint("id", "user_id", name="uq_articles_id_user_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(
        String(16), nullable=False, default="text", server_default="text"
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False, server_default="de")
    last_opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reading_position: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Present only when kind == "song". Deletion is left to the database's ON DELETE CASCADE
    # (passive_deletes) rather than having the ORM load the song just to delete it.
    song: Mapped["Song | None"] = relationship(
        back_populates="article",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
