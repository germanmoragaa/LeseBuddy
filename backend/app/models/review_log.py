import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class ReviewLog(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Append-only: never updated or deleted by the app, see
    docs/decisions/0005-spaced-repetition.md. `flashcard_id` is SET NULL (not CASCADE) so a
    deleted vocabulary item's review history survives for analytics even once its card is
    gone; `lemma` is a snapshot taken at review time for the same reason the flashcard itself
    can't be joined back to reliably forever.
    """

    __tablename__ = "review_logs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    flashcard_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("flashcards.id", ondelete="SET NULL"), nullable=True
    )
    lemma: Mapped[str] = mapped_column(String(255), nullable=False)
    rating: Mapped[str] = mapped_column(String(16), nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    previous_ease_factor: Mapped[float] = mapped_column(Float, nullable=False)
    previous_interval_days: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    new_ease_factor: Mapped[float] = mapped_column(Float, nullable=False)
    new_interval_days: Mapped[int] = mapped_column(Integer, nullable=False)
    new_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scheduler_version: Mapped[int] = mapped_column(Integer, nullable=False)
    # Lets a retried/double-submitted review request be replayed idempotently instead of
    # re-applying the scheduler a second time — see review_service.submit_review.
    client_review_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, unique=True
    )

    __table_args__ = (Index("ix_review_logs_user_id_reviewed_at", "user_id", "reviewed_at"),)
