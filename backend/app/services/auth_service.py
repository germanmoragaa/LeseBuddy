from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    generate_session_token,
    hash_password,
    hash_token,
    verify_dummy_password,
    verify_password,
)
from app.models import LoginAttempt, User, UserSession
from app.schemas.auth import RegisterRequest, UserMe

LOCKOUT_THRESHOLD = 5
LOCKOUT_WINDOW = timedelta(minutes=15)


class UsernameTakenError(Exception):
    """Raised when a username is already in use (case-insensitively)."""


class EmailTakenError(Exception):
    """Raised when an email is already in use."""


class AccountLockedError(Exception):
    """Raised when an identifier has too many recent failed login attempts."""


def _find_user_by_username(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.username) == username.lower()))


def _find_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def register_user(db: Session, data: RegisterRequest) -> User:
    if _find_user_by_username(db, data.username) is not None:
        raise UsernameTakenError
    if _find_user_by_email(db, data.email) is not None:
        raise EmailTakenError

    user = User(
        username=data.username,
        email=data.email,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Pre-checks above close the common case; this catches the rare race where two
        # requests for the same username/email commit concurrently.
        db.rollback()
        if _find_user_by_username(db, data.username) is not None:
            raise UsernameTakenError from None
        raise EmailTakenError from None
    db.refresh(user)

    # TODO(email-confirmation): send a verification email to user.email here. Nothing else
    # about this function's contract needs to change when that feature is added.

    return user


def authenticate_user(db: Session, identifier: str, password: str) -> User | None:
    """Returns the matching user, or None if the identifier/password pair is invalid.

    Raises AccountLockedError if this identifier has too many recent failed attempts.
    Looks and behaves identically whether or not `identifier` maps to a real account, so
    the lockout itself can't be used to tell real accounts from made-up ones.
    """
    normalized_identifier = identifier.strip().lower()
    window_start = datetime.now(UTC) - LOCKOUT_WINDOW

    failed_attempts = db.scalar(
        select(func.count())
        .select_from(LoginAttempt)
        .where(
            LoginAttempt.identifier == normalized_identifier,
            LoginAttempt.succeeded.is_(False),
            LoginAttempt.created_at > window_start,
        )
    )
    if failed_attempts and failed_attempts >= LOCKOUT_THRESHOLD:
        raise AccountLockedError

    user = db.scalar(
        select(User).where(
            or_(
                func.lower(User.username) == normalized_identifier,
                User.email == normalized_identifier,
            )
        )
    )

    if user is None:
        verify_dummy_password()
        db.add(LoginAttempt(identifier=normalized_identifier, succeeded=False))
        db.commit()
        return None

    if not verify_password(password, user.password_hash):
        db.add(LoginAttempt(identifier=normalized_identifier, succeeded=False))
        db.commit()
        return None

    return user


def create_session(db: Session, user: User) -> tuple[UserSession, str]:
    raw_token = generate_session_token()
    session = UserSession(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=datetime.now(UTC) + timedelta(days=get_settings().session_duration_days),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session, raw_token


def get_user_for_token(db: Session, raw_token: str) -> User | None:
    token_hash = hash_token(raw_token)
    session = db.scalar(select(UserSession).where(UserSession.token_hash == token_hash))

    if session is None or session.expires_at < datetime.now(UTC):
        return None

    session.last_used_at = datetime.now(UTC)
    db.commit()

    return db.get(User, session.user_id)


def revoke_session(db: Session, raw_token: str) -> None:
    db.execute(delete(UserSession).where(UserSession.token_hash == hash_token(raw_token)))
    db.commit()


def to_user_me(user: User) -> UserMe:
    return UserMe(
        id=user.id,
        username=user.username,
        email=user.email,
        email_verified=user.email_verified_at is not None,
        created_at=user.created_at,
    )
