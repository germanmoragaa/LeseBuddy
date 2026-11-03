import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_email_sender
from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import SESSION_COOKIE_NAME
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, UserMe, VerifyEmailRequest
from app.services.auth_service import (
    AccountLockedError,
    CodeExpiredError,
    EmailTakenError,
    InvalidCodeError,
    NoActiveCodeError,
    ResendCooldownError,
    ResendHourlyCapError,
    TooManyAttemptsError,
    UsernameTakenError,
    authenticate_user,
    create_session,
    issue_verification_code,
    register_user,
    revoke_session,
    to_user_me,
    verify_email_code,
)
from app.services.email import EmailMessage, EmailSender, render_verification_email

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

logger = logging.getLogger(__name__)


def _send_verification_email(email_sender: EmailSender, to: str, code: str) -> None:
    settings = get_settings()
    subject, text_body, html_body = render_verification_email(
        code, settings.verification_code_ttl_minutes
    )
    try:
        email_sender.send(
            EmailMessage(to=to, subject=subject, text_body=text_body, html_body=html_body)
        )
    except Exception:  # noqa: BLE001 - never let a background email failure surface anywhere;
        # the user's recovery path is the resend button.
        logger.exception("Failed to send verification email to %s", to)


def _set_session_cookie(response: Response, raw_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
        path="/",
        max_age=settings.session_duration_days * 24 * 60 * 60,
    )


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserMe)
def register(
    data: RegisterRequest,
    response: Response,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    email_sender: EmailSender = Depends(get_email_sender),
) -> UserMe:
    try:
        user = register_user(db, data)
    except UsernameTakenError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=[
                {
                    "loc": ["body", "username"],
                    "msg": "This username is already taken.",
                    "type": "value_error.conflict",
                }
            ],
        ) from None
    except EmailTakenError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=[
                {
                    "loc": ["body", "email"],
                    "msg": "This email is already registered.",
                    "type": "value_error.conflict",
                }
            ],
        ) from None

    # Send only after the user is committed, and never let a send failure fail registration
    # itself — the user can always ask for a new code from /verify-email.
    _, plaintext_code = issue_verification_code(db, user)
    background_tasks.add_task(_send_verification_email, email_sender, user.email, plaintext_code)

    _, raw_token = create_session(db, user)
    _set_session_cookie(response, raw_token)
    return to_user_me(user)


@router.post("/login", response_model=UserMe)
def login(data: LoginRequest, response: Response, db: Session = Depends(get_db)) -> UserMe:
    try:
        user = authenticate_user(db, data.identifier, data.password)
    except AccountLockedError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please try again in 15 minutes.",
        ) from None

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/username or password.",
        )

    _, raw_token = create_session(db, user)
    _set_session_cookie(response, raw_token)
    return to_user_me(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> None:
    raw_token = request.cookies.get(SESSION_COOKIE_NAME)
    if raw_token is not None:
        revoke_session(db, raw_token)
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")


@router.post("/verify-email", response_model=UserMe)
def verify_email(
    data: VerifyEmailRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserMe:
    try:
        verify_email_code(db, user, data.code)
    except NoActiveCodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "no_active_code",
                "message": "No active verification code. Please request a new code.",
            },
        ) from None
    except CodeExpiredError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "code_expired",
                "message": "This code has expired. Please request a new code.",
            },
        ) from None
    except TooManyAttemptsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "too_many_attempts",
                "message": "Too many incorrect attempts. Please request a new code.",
            },
        ) from None
    except InvalidCodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_code", "message": "Incorrect code. Please try again."},
        ) from None

    return to_user_me(user)


@router.post("/resend-verification", status_code=status.HTTP_204_NO_CONTENT)
def resend_verification(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    email_sender: EmailSender = Depends(get_email_sender),
) -> None:
    if user.email_verified_at is not None:
        return None

    try:
        _, plaintext_code = issue_verification_code(db, user)
    except ResendCooldownError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "resend_cooldown", "retry_after": exc.retry_after},
        ) from None
    except ResendHourlyCapError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "resend_hourly_cap", "retry_after": exc.retry_after},
        ) from None

    background_tasks.add_task(_send_verification_email, email_sender, user.email, plaintext_code)
    return None
