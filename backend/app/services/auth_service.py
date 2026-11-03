from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    generate_session_token,
    generate_verification_code,
    hash_password,
    hash_token,
    hash_verification_code,
    verify_dummy_password,
    verify_password,
    verify_verification_code,
)
from app.models import EmailVerificationCode, LoginAttempt, User, UserSession
from app.schemas.auth import RegisterRequest, UserMe

LOCKOUT_THRESHOLD = 5
LOCKOUT_WINDOW = timedelta(minutes=15)


class UsernameTakenError(Exception):
    """Raised when a username is already in use (case-insensitively)."""


class EmailTakenError(Exception):
    """Raised when an email is already in use."""


class AccountLockedError(Exception):
    """Raised when an identifier has too many recent failed login attempts."""


class ResendCooldownError(Exception):
    """Raised when a new code is requested before the per-request cooldown has elapsed."""

    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after


class ResendHourlyCapError(Exception):
    """Raised when a user has requested too many codes within the last hour."""

    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after


class NoActiveCodeError(Exception):
    """Raised when verifying but no (unconsumed) code has ever been issued."""


class CodeExpiredError(Exception):
    """Raised when the latest active code's TTL has passed."""


class TooManyAttemptsError(Exception):
    """Raised when the latest active code has already hit the attempt limit."""


class InvalidCodeError(Exception):
    """Raised when the submitted code doesn't match the latest active code."""


def _find_user_by_username(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.username) == username.lower()))


def _find_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.email) == email.lower()))


def _expire_stale_unverified_account(db: Session, username: str, email: str) -> None:
    """Deletes an unverified account occupying this username/email if it's past its TTL.

    Runs as part of the caller's open transaction (flush, not commit): the delete becomes
    visible to the uniqueness checks that follow in the same transaction, and everything
    commits together with the new user at the end, so there's no window where the slot is
    freed but a concurrent request could fail to claim it.
    """
    cutoff = datetime.now(UTC) - timedelta(hours=get_settings().unverified_account_ttl_hours)
    stale_user = db.scalar(
        select(User).where(
            or_(
                func.lower(User.username) == username.lower(),
                func.lower(User.email) == email.lower(),
            ),
            User.email_verified_at.is_(None),
            User.created_at < cutoff,
        )
    )
    if stale_user is not None:
        db.delete(stale_user)
        db.flush()


def register_user(db: Session, data: RegisterRequest) -> User:
    _expire_stale_unverified_account(db, data.username, data.email)

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

    return user


def issue_verification_code(db: Session, user: User) -> tuple[EmailVerificationCode, str]:
    """Issues a new verification code for `user`, invalidating any still-active one.

    Enforces a per-request cooldown and an hourly cap, each raising a typed error carrying
    how many seconds remain. Returns the stored record and the one-time plaintext code (the
    only place the plaintext ever exists outside the user's inbox).
    """
    settings = get_settings()
    now = datetime.now(UTC)

    latest_code = db.scalar(
        select(EmailVerificationCode)
        .where(EmailVerificationCode.user_id == user.id)
        .order_by(EmailVerificationCode.created_at.desc())
    )
    if latest_code is not None:
        cooldown = settings.verification_resend_cooldown_seconds
        elapsed = (now - latest_code.created_at).total_seconds()
        if elapsed < cooldown:
            raise ResendCooldownError(retry_after=int(cooldown - elapsed) + 1)

    hour_ago = now - timedelta(hours=1)
    codes_in_last_hour = db.scalars(
        select(EmailVerificationCode)
        .where(
            EmailVerificationCode.user_id == user.id,
            EmailVerificationCode.created_at > hour_ago,
        )
        .order_by(EmailVerificationCode.created_at.asc())
    ).all()
    if len(codes_in_last_hour) >= settings.verification_resend_hourly_cap:
        oldest_in_window = codes_in_last_hour[0]
        elapsed = (now - oldest_in_window.created_at).total_seconds()
        raise ResendHourlyCapError(retry_after=int(3600 - elapsed) + 1)

    db.execute(
        update(EmailVerificationCode)
        .where(
            EmailVerificationCode.user_id == user.id,
            EmailVerificationCode.consumed_at.is_(None),
        )
        .values(consumed_at=now)
    )

    plaintext_code = generate_verification_code()
    record = EmailVerificationCode(
        user_id=user.id,
        code_hash=hash_verification_code(plaintext_code, settings.secret_key),
        expires_at=now + timedelta(minutes=settings.verification_code_ttl_minutes),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record, plaintext_code


def verify_email_code(db: Session, user: User, submitted_code: str) -> None:
    """Verifies `submitted_code` against the latest active code for `user`.

    A no-op if the user is already verified, so re-submitting a stale form can't error.
    """
    if user.email_verified_at is not None:
        return

    settings = get_settings()
    code_record = db.scalar(
        select(EmailVerificationCode)
        .where(
            EmailVerificationCode.user_id == user.id,
            EmailVerificationCode.consumed_at.is_(None),
        )
        .order_by(EmailVerificationCode.created_at.desc())
    )
    if code_record is None:
        raise NoActiveCodeError
    if code_record.expires_at < datetime.now(UTC):
        raise CodeExpiredError
    if code_record.attempts >= settings.verification_code_max_attempts:
        raise TooManyAttemptsError

    if not verify_verification_code(submitted_code, code_record.code_hash, settings.secret_key):
        code_record.attempts += 1
        db.commit()
        raise InvalidCodeError

    now = datetime.now(UTC)
    code_record.consumed_at = now
    user.email_verified_at = now
    db.commit()


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
