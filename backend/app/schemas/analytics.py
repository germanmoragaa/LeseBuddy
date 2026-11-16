from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class StreakInfo(BaseModel):
    current_days: int
    longest_days: int
    # Oldest to newest, always exactly 7 entries (today is the last one) - an active day is
    # at least one review_log or vocabulary_item created that local day, see
    # analytics_service._compute_streak.
    last_7_days: list[bool]


class Recommendation(BaseModel):
    type: Literal["review", "continue_reading", "add_text"]
    reason: str
    article_id: UUID | None = None


class AnalyticsOverview(BaseModel):
    words_saved: int
    words_mature: int
    words_saved_this_week: int
    reviews_today: int
    reviews_this_week: int
    due_now: int
    texts_opened_this_week: int
    streak: StreakInfo
    recommendation: Recommendation


class RatingCounts(BaseModel):
    again: int
    hard: int
    good: int
    easy: int


class RatingPercentages(BaseModel):
    again: float
    hard: float
    good: float
    easy: float


class DayActivity(BaseModel):
    date: date
    reviews: int
    words_saved: int
    cumulative_vocabulary: int


class AnalyticsActivity(BaseModel):
    days: list[DayActivity]
    rating_counts: RatingCounts
    rating_percentages: RatingPercentages
    # None when there were zero reviews in range on cards that weren't new (nothing to take a
    # retention rate over) - never reported as a misleading 0%.
    retention_percent: float | None
