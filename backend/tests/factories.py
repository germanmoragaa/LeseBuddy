from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import User

DEFAULT_PASSWORD = "correct horse battery staple"


def make_user(
    db_session: Session,
    *,
    email: str,
    username: str = "testuser",
    password: str = DEFAULT_PASSWORD,
    email_verified: bool = False,
    created_at: datetime | None = None,
) -> User:
    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        email_verified_at=datetime.now(UTC) if email_verified else None,
    )
    if created_at is not None:
        user.created_at = created_at
    db_session.add(user)
    db_session.flush()
    return user
