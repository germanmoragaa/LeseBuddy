"""Real usage analytics for the dashboard and progress screen - replaces every mocked
dashboard/progress metric with a number actually derived from this user's own rows. No
metric is shown unless it's measurable from existing tables (flashcards, review_logs,
vocabulary_items, articles); see docs/blueprint.md backlog items 12 and 16.

All day/week boundaries are computed in the caller-supplied IANA timezone (the browser's own
zone, validated with zoneinfo by the API layer - see app/api/analytics.py), not the server's.
Boundaries are converted to absolute UTC instants in Python and compared with plain
`>=`/`<` against the existing timestamptz columns, so the existing
(user_id, reviewed_at)/(user_id, created_at) indexes still apply - the `AT TIME ZONE`
conversion is reserved for the handful of places that need a value grouped *by* local date
(the day-activity series and the streak's distinct active dates), not for simple range filters.
"""

import uuid
from datetime import UTC, date, datetime, time, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

from app.models import Article, Flashcard, ReviewLog, User, VocabularyItem
from app.services.article_service import list_articles_for_user
from app.services.review_service import get_summary
from app.services.scheduler import RATINGS

# A card stops being "new" and becomes a settled part of the user's vocabulary once its
# interval has grown past three weeks - an editorial threshold, not derived from the
# scheduler itself.
MATURE_INTERVAL_DAYS = 21
RECENT_ARTICLES_TO_SCAN = 20


def _local_midnight_utc(local_date: date, tz: str) -> datetime:
    """The absolute UTC instant of 00:00 on `local_date` in `tz` - ready to compare against a
    timestamptz column directly with plain `>=`/`<`."""
    return datetime.combine(local_date, time.min, tzinfo=ZoneInfo(tz)).astimezone(UTC)


def _local_day_bounds(now: datetime, tz: str) -> tuple[date, datetime, datetime]:
    """Returns (today's local date, that day's start, that day's end) - the last two as
    absolute UTC instants."""
    today_local = now.astimezone(ZoneInfo(tz)).date()
    day_start = _local_midnight_utc(today_local, tz)
    return today_local, day_start, day_start + timedelta(days=1)


def _local_week_start(today_local: date, tz: str) -> datetime:
    """Monday 00:00 of the week containing `today_local`, as an absolute UTC instant."""
    monday = today_local - timedelta(days=today_local.isoweekday() - 1)
    return _local_midnight_utc(monday, tz)


def _vocabulary_count(db: Session, *filters) -> int:
    return db.scalar(select(func.count()).select_from(VocabularyItem).where(*filters)) or 0


def _active_local_dates(db: Session, user: User, tz: str) -> set[date]:
    """Every distinct local calendar date (ever) on which the user reviewed a card or saved
    a word - the raw material for both the current and the longest-ever streak."""
    review_dates = db.scalars(
        select(cast(func.timezone(tz, ReviewLog.reviewed_at), Date))
        .where(ReviewLog.user_id == user.id)
        .distinct()
    ).all()
    vocab_dates = db.scalars(
        select(cast(func.timezone(tz, VocabularyItem.created_at), Date))
        .where(VocabularyItem.user_id == user.id)
        .distinct()
    ).all()
    return set(review_dates) | set(vocab_dates)


def _compute_streak(active_dates: set[date], today_local: date) -> tuple[int, int, list[bool]]:
    last_7_days = [
        (today_local - timedelta(days=offset)) in active_dates for offset in range(6, -1, -1)
    ]

    if not active_dates:
        return 0, 0, last_7_days

    longest = 1
    run = 1
    # The two sorted lists are deliberately offset by one element (pairing each date with
    # the next) - strict=True would be wrong here, not a safety check.
    for earlier, later in zip(sorted(active_dates), sorted(active_dates)[1:], strict=False):
        run = run + 1 if later == earlier + timedelta(days=1) else 1
        longest = max(longest, run)

    # A day that hasn't happened yet doesn't break the streak - only check it as a possible
    # starting point, falling back to yesterday when today has no activity yet.
    cursor = today_local if today_local in active_dates else today_local - timedelta(days=1)
    current = 0
    while cursor in active_dates:
        current += 1
        cursor -= timedelta(days=1)

    return current, longest, last_7_days


def _recommendation(
    db: Session, user: User, now: datetime, due_now: int
) -> tuple[Literal["review", "continue_reading", "add_text"], str, uuid.UUID | None]:
    if due_now > 0:
        card_word = "card" if due_now == 1 else "cards"
        return "review", f"You have {due_now} {card_word} due", None

    recent_articles = list_articles_for_user(
        db, user, page=1, page_size=RECENT_ARTICLES_TO_SCAN, sort="recent"
    )
    for article, progress_percent in recent_articles:
        if progress_percent is None or progress_percent < 100:
            title = article.title or "your text"
            return "continue_reading", f'Pick up where you left off in "{title}"', article.id

    return "add_text", "Add a new text to keep building your vocabulary", None


def get_overview(db: Session, user: User, tz: str, now: datetime) -> dict:
    today_local, day_start, day_end = _local_day_bounds(now, tz)
    week_start = _local_week_start(today_local, tz)

    words_saved = _vocabulary_count(db, VocabularyItem.user_id == user.id)
    words_saved_this_week = _vocabulary_count(
        db,
        VocabularyItem.user_id == user.id,
        VocabularyItem.created_at >= week_start,
        VocabularyItem.created_at < day_end,
    )
    words_mature = (
        db.scalar(
            select(func.count())
            .select_from(Flashcard)
            .where(Flashcard.user_id == user.id, Flashcard.interval_days >= MATURE_INTERVAL_DAYS)
        )
        or 0
    )
    reviews_today = (
        db.scalar(
            select(func.count())
            .select_from(ReviewLog)
            .where(
                ReviewLog.user_id == user.id,
                ReviewLog.reviewed_at >= day_start,
                ReviewLog.reviewed_at < day_end,
            )
        )
        or 0
    )
    reviews_this_week = (
        db.scalar(
            select(func.count())
            .select_from(ReviewLog)
            .where(
                ReviewLog.user_id == user.id,
                ReviewLog.reviewed_at >= week_start,
                ReviewLog.reviewed_at < day_end,
            )
        )
        or 0
    )
    texts_opened_this_week = (
        db.scalar(
            select(func.count())
            .select_from(Article)
            .where(
                Article.user_id == user.id,
                Article.last_opened_at >= week_start,
                Article.last_opened_at < day_end,
            )
        )
        or 0
    )
    due_now, _next_due_at, _total_cards = get_summary(db, user, now)

    active_dates = _active_local_dates(db, user, tz)
    current_days, longest_days, last_7_days = _compute_streak(active_dates, today_local)

    recommendation_type, reason, article_id = _recommendation(db, user, now, due_now)

    return {
        "words_saved": words_saved,
        "words_mature": words_mature,
        "words_saved_this_week": words_saved_this_week,
        "reviews_today": reviews_today,
        "reviews_this_week": reviews_this_week,
        "due_now": due_now,
        "texts_opened_this_week": texts_opened_this_week,
        "streak": {
            "current_days": current_days,
            "longest_days": longest_days,
            "last_7_days": last_7_days,
        },
        "recommendation": {"type": recommendation_type, "reason": reason, "article_id": article_id},
    }


def get_activity(db: Session, user: User, tz: str, now: datetime, days: int) -> dict:
    today_local, _day_start, day_end = _local_day_bounds(now, tz)
    range_start_date = today_local - timedelta(days=days - 1)
    range_start = _local_midnight_utc(range_start_date, tz)

    reviews_local_date = cast(func.timezone(tz, ReviewLog.reviewed_at), Date)
    reviews_by_date = dict(
        db.execute(
            select(reviews_local_date, func.count())
            .where(
                ReviewLog.user_id == user.id,
                ReviewLog.reviewed_at >= range_start,
                ReviewLog.reviewed_at < day_end,
            )
            .group_by(reviews_local_date)
        ).all()
    )

    words_local_date = cast(func.timezone(tz, VocabularyItem.created_at), Date)
    words_by_date = dict(
        db.execute(
            select(words_local_date, func.count())
            .where(
                VocabularyItem.user_id == user.id,
                VocabularyItem.created_at >= range_start,
                VocabularyItem.created_at < day_end,
            )
            .group_by(words_local_date)
        ).all()
    )

    baseline_vocabulary = _vocabulary_count(
        db, VocabularyItem.user_id == user.id, VocabularyItem.created_at < range_start
    )

    day_points = []
    running_total = baseline_vocabulary
    for offset in range(days):
        day = range_start_date + timedelta(days=offset)
        reviews = reviews_by_date.get(day, 0)
        words_saved = words_by_date.get(day, 0)
        running_total += words_saved
        day_points.append(
            {
                "date": day,
                "reviews": reviews,
                "words_saved": words_saved,
                "cumulative_vocabulary": running_total,
            }
        )

    rating_rows = dict(
        db.execute(
            select(ReviewLog.rating, func.count())
            .where(
                ReviewLog.user_id == user.id,
                ReviewLog.reviewed_at >= range_start,
                ReviewLog.reviewed_at < day_end,
            )
            .group_by(ReviewLog.rating)
        ).all()
    )
    rating_counts = {rating: rating_rows.get(rating, 0) for rating in RATINGS}
    total_ratings = sum(rating_counts.values())
    rating_percentages = {
        rating: (count / total_ratings * 100 if total_ratings else 0.0)
        for rating, count in rating_counts.items()
    }

    not_new_total = (
        db.scalar(
            select(func.count())
            .select_from(ReviewLog)
            .where(
                ReviewLog.user_id == user.id,
                ReviewLog.reviewed_at >= range_start,
                ReviewLog.reviewed_at < day_end,
                ReviewLog.previous_interval_days > 0,
            )
        )
        or 0
    )
    not_new_retained = (
        db.scalar(
            select(func.count())
            .select_from(ReviewLog)
            .where(
                ReviewLog.user_id == user.id,
                ReviewLog.reviewed_at >= range_start,
                ReviewLog.reviewed_at < day_end,
                ReviewLog.previous_interval_days > 0,
                ReviewLog.rating != "again",
            )
        )
        or 0
    )
    retention_percent = (not_new_retained / not_new_total * 100) if not_new_total else None

    return {
        "days": day_points,
        "rating_counts": rating_counts,
        "rating_percentages": rating_percentages,
        "retention_percent": retention_percent,
    }
