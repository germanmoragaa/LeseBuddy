from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models import User
from app.schemas.auth import UserMe
from app.services.auth_service import to_user_me

router = APIRouter(prefix="/api/v1", tags=["users"])


@router.get("/me", response_model=UserMe)
def read_current_user(current_user: User = Depends(get_current_user)) -> UserMe:
    return to_user_me(current_user)
