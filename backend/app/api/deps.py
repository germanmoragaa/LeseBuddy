from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import SESSION_COOKIE_NAME
from app.models import User
from app.services.auth_service import get_user_for_token
from app.services.email import EmailSender, SmtpEmailSender


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    raw_token = request.cookies.get(SESSION_COOKIE_NAME)
    if raw_token is not None:
        user = get_user_for_token(db, raw_token)
        if user is not None:
            return user

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def get_current_verified_user(user: User = Depends(get_current_user)) -> User:
    if user.email_verified_at is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "email_not_verified",
                "message": "Please verify your email address to continue.",
            },
        )
    return user


def get_email_sender() -> EmailSender:
    return SmtpEmailSender(get_settings())
