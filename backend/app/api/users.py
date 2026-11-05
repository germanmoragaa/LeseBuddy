from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models import User
from app.schemas.auth import UpdateSettingsRequest, UserMe
from app.services.auth_service import to_user_me, update_translation_language

router = APIRouter(prefix="/api/v1", tags=["users"])


@router.get("/me", response_model=UserMe)
def read_current_user(current_user: User = Depends(get_current_user)) -> UserMe:
    return to_user_me(current_user)


@router.patch("/me", response_model=UserMe)
def update_current_user_settings(
    data: UpdateSettingsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserMe:
    updated = update_translation_language(db, current_user, data.translation_language)
    return to_user_me(updated)
