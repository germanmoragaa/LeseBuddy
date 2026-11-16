from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_clock, get_current_verified_user
from app.core.db import get_db
from app.models import User
from app.schemas.analytics import AnalyticsActivity, AnalyticsOverview
from app.services.analytics_service import get_activity, get_overview

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


VALID_ACTIVITY_DAYS = (7, 30, 90)


def validated_timezone(tz: str = Query(default="UTC")) -> str:
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"Unknown timezone: {tz!r}"
        ) from None
    return tz


def validated_activity_days(days: int = Query(default=7)) -> int:
    # A plain int (rather than Literal[7, 30, 90]) because FastAPI/Pydantic doesn't coerce a
    # query string into a Literal's int members the way it does for a plain `int` field -
    # validated by hand here instead of relying on that.
    if days not in VALID_ACTIVITY_DAYS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"days must be one of {VALID_ACTIVITY_DAYS}",
        )
    return days


@router.get("/overview", response_model=AnalyticsOverview)
def get_overview_endpoint(
    tz: str = Depends(validated_timezone),
    user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
    now_fn: Callable[[], datetime] = Depends(get_clock),
) -> AnalyticsOverview:
    return AnalyticsOverview.model_validate(get_overview(db, user, tz, now_fn()))


@router.get("/activity", response_model=AnalyticsActivity)
def get_activity_endpoint(
    tz: str = Depends(validated_timezone),
    days: int = Depends(validated_activity_days),
    user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
    now_fn: Callable[[], datetime] = Depends(get_clock),
) -> AnalyticsActivity:
    return AnalyticsActivity.model_validate(get_activity(db, user, tz, now_fn(), days))
