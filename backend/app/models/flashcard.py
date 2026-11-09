import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Flashcard(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One per vocabulary item (see the unique FK below) — scheduling state only; the
    reviewable content (display form, meaning, translation) is read from the associated
    VocabularyItem, never duplicated here. See docs/decisions/0005-spaced-repetition.md.
    """

    __tablename__ = "flashcards"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vocabulary_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vocabulary_items.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    ease_factor: Mapped[float] = mapped_column(Float, nullable=False, server_default="2.5")
    interval_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    repetitions: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    lapses: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (Index("ix_flashcards_user_id_due_at", "user_id", "due_at"),)
