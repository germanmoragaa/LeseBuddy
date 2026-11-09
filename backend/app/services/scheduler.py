"""Deterministic SM-2-adapted spaced-repetition scheduler — see
docs/decisions/0005-spaced-repetition.md. Pure functions only: no randomness/fuzz, no I/O, no
clock reads. Callers (app/services/review_service.py) own persistence and `now`.
"""

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Literal

# Bump by hand whenever the scheduling rules change — existing review_logs rows keep the
# version that was in effect when they were written, mirroring
# analysis_service.CURRENT_ANALYSIS_VERSION's "history, not silently overwritten" rule.
SCHEDULER_VERSION = 1

Rating = Literal["again", "hard", "good", "easy"]
RATINGS: tuple[Rating, ...] = ("again", "hard", "good", "easy")

EASE_FLOOR = 1.3
INTERVAL_CAP_DAYS = 365
AGAIN_DELAY = timedelta(minutes=10)


@dataclass(frozen=True)
class CardState:
    ease_factor: float
    interval_days: int
    repetitions: int
    lapses: int
    due_at: datetime


def _raw_intervals(ease_factor: float, interval_days: int, repetitions: int) -> dict[str, int]:
    """Computes hard/good/easy's hypothetical next interval from the same starting state,
    each independently per the rules — none of these three depend on another rating's ease
    adjustment, only on the card's current (pre-review) ease/interval/repetitions."""
    hard = 1 if repetitions == 0 else max(1, round(interval_days * 1.2))

    if repetitions == 0:
        good = 1
    elif repetitions == 1:
        good = 3
    else:
        good = max(1, round(interval_days * ease_factor))

    easy = 4 if repetitions == 0 else max(1, round(good * 1.3))

    return {"hard": hard, "good": good, "easy": easy}


def _clamped_intervals(ease_factor: float, interval_days: int, repetitions: int) -> dict[str, int]:
    """Enforces the required hard<=good<=easy ordering and the 365-day cap. The raw formulas
    already satisfy this for the common case (ease_factor >= EASE_FLOOR > 1.2), but an unusual
    prior history (e.g. a lone "easy" immediately before a "hard" preview) can make the raw
    hard interval briefly exceed the raw good interval — clamping here guarantees the invariant
    always holds instead of only "usually"."""
    raw = _raw_intervals(ease_factor, interval_days, repetitions)
    hard = raw["hard"]
    good = max(raw["good"], hard)
    easy = max(raw["easy"], good)
    return {
        "hard": min(hard, INTERVAL_CAP_DAYS),
        "good": min(good, INTERVAL_CAP_DAYS),
        "easy": min(easy, INTERVAL_CAP_DAYS),
    }


def preview(state: CardState, now: datetime) -> dict[Rating, int]:
    """Returns the interval (in days) each rating button would produce from this state,
    without mutating it — used to render "in N days" hints on the four rating buttons."""
    intervals = _clamped_intervals(state.ease_factor, state.interval_days, state.repetitions)
    return {
        "again": 0,
        "hard": intervals["hard"],
        "good": intervals["good"],
        "easy": intervals["easy"],
    }


def schedule(state: CardState, rating: Rating, now: datetime) -> CardState:
    """Applies one review rating to `state` and returns the new state. Pure and deterministic:
    the same (state, rating, now) always produces the same result, with no fuzz/jitter."""
    if rating == "again":
        return replace(
            state,
            ease_factor=max(EASE_FLOOR, state.ease_factor - 0.20),
            interval_days=0,
            repetitions=0,
            lapses=state.lapses + 1,
            due_at=now + AGAIN_DELAY,
        )

    intervals = _clamped_intervals(state.ease_factor, state.interval_days, state.repetitions)

    if rating == "hard":
        new_ease = max(EASE_FLOOR, state.ease_factor - 0.15)
        interval_days = intervals["hard"]
    elif rating == "good":
        new_ease = state.ease_factor
        interval_days = intervals["good"]
    else:  # easy
        new_ease = state.ease_factor + 0.15
        interval_days = intervals["easy"]

    return replace(
        state,
        ease_factor=new_ease,
        interval_days=interval_days,
        repetitions=state.repetitions + 1,
        due_at=now + timedelta(days=interval_days),
    )
