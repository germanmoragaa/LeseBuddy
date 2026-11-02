from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class LoginAttempt(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Logs failed login attempts keyed by the raw identifier the client sent (not a
    resolved user_id), so brute-force lockout behaves identically for real and made-up
    identifiers and doesn't itself leak which accounts exist."""

    __tablename__ = "login_attempts"

    identifier: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    succeeded: Mapped[bool] = mapped_column(Boolean, nullable=False)
