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
) -> User:
    user = User(username=username, email=email, password_hash=hash_password(password))
    db_session.add(user)
    db_session.flush()
    return user
