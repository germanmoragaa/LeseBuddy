from fastapi import APIRouter, Depends

from app.api.deps import get_current_verified_user
from app.models import User

router = APIRouter(prefix="/api/v1/articles", tags=["articles"])


@router.get("")
def list_articles(user: User = Depends(get_current_verified_user)) -> list[dict]:
    # Placeholder standing in for real article persistence (a future step); exists here to
    # exercise get_current_verified_user end-to-end over HTTP.
    return []
