from datetime import datetime

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(30), nullable=False)
    # No unique=True here: email is always stored lowercase (normalized in the request schema),
    # but the uniqueness guarantee itself lives in the ix_users_email_lower functional index
    # below, so it holds at the DB level even if some future write path forgets to normalize.
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # DeepL target-language code (e.g. "EN-US", "ES") — not a plain ISO 639-1 code, since
    # DeepL requires a regional variant for English. Always has a value; new users get the
    # server default below, matching Settings.translation_default_language's default.
    translation_language: Mapped[str] = mapped_column(
        String(8), nullable=False, server_default="EN-US"
    )

    __table_args__ = (
        Index("ix_users_username_lower", func.lower(username), unique=True),
        Index("ix_users_email_lower", func.lower(email), unique=True),
    )
