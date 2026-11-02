from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import SESSION_COOKIE_NAME
from app.schemas.auth import LoginRequest, RegisterRequest, UserMe
from app.services.auth_service import (
    AccountLockedError,
    EmailTakenError,
    UsernameTakenError,
    authenticate_user,
    create_session,
    register_user,
    revoke_session,
    to_user_me,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


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
def register(data: RegisterRequest, response: Response, db: Session = Depends(get_db)) -> UserMe:
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
