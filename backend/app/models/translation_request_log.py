import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class TranslationRequestLog(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One row per successful, non-cached translation request — mirrors LoginAttempt's
    window-counted rate-limit pattern. Cache hits never reach this table (gated on "did we
    actually call the provider", not on "did the user ask"), so cached lookups can't trip
    the rate limit."""

    __tablename__ = "translation_request_log"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
