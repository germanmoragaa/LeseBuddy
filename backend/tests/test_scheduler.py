from datetime import UTC, datetime, timedelta

import pytest

from app.services.scheduler import (
    EASE_FLOOR,
    INTERVAL_CAP_DAYS,
    RATINGS,
    CardState,
    preview,
    schedule,
)

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


def new_card(**overrides) -> CardState:
    defaults = dict(
        ease_factor=2.5,
        interval_days=0,
        repetitions=0,
        lapses=0,
        due_at=NOW,
    )
    defaults.update(overrides)
    return CardState(**defaults)


class TestNewCard:
    """A brand-new card: repetitions == 0, default ease 2.5."""

    def test_again(self):
        new_state = schedule(new_card(), "again", NOW)
        assert new_state.ease_factor == pytest.approx(2.3)
        assert new_state.interval_days == 0
        assert new_state.repetitions == 0
        assert new_state.lapses == 1
        assert new_state.due_at == NOW + timedelta(minutes=10)

    def test_hard(self):
        new_state = schedule(new_card(), "hard", NOW)
        assert new_state.ease_factor == pytest.approx(2.35)
        assert new_state.interval_days == 1
        assert new_state.repetitions == 1
        assert new_state.due_at == NOW + timedelta(days=1)

    def test_good(self):
        new_state = schedule(new_card(), "good", NOW)
        assert new_state.ease_factor == pytest.approx(2.5)
        assert new_state.interval_days == 1
        assert new_state.repetitions == 1

    def test_easy(self):
        new_state = schedule(new_card(), "easy", NOW)
        assert new_state.ease_factor == pytest.approx(2.65)
        assert new_state.interval_days == 4
        assert new_state.repetitions == 1


class TestSecondReview:
    """repetitions == 1 — good has a fixed 3-day interval regardless of the prior interval."""

    def test_good_is_fixed_at_three_days(self):
        state = new_card(ease_factor=2.5, interval_days=1, repetitions=1)
        new_state = schedule(state, "good", NOW)
        assert new_state.interval_days == 3
        assert new_state.repetitions == 2

    def test_hard_uses_the_general_formula(self):
        state = new_card(ease_factor=2.5, interval_days=1, repetitions=1)
        new_state = schedule(state, "hard", NOW)
        assert new_state.interval_days == 1  # max(1, round(1 * 1.2)) == 1

    def test_easy_derives_from_the_good_interval(self):
        state = new_card(ease_factor=2.5, interval_days=1, repetitions=1)
        new_state = schedule(state, "easy", NOW)
        assert new_state.interval_days == 4  # round(3 * 1.3) == 4


class TestMatureCard:
    """repetitions >= 2 — good/easy scale with the current interval and ease factor."""

    def test_good_multiplies_interval_by_ease(self):
        state = new_card(ease_factor=2.4, interval_days=10, repetitions=3)
        new_state = schedule(state, "good", NOW)
        assert new_state.interval_days == 24  # round(10 * 2.4)
        assert new_state.ease_factor == pytest.approx(2.4)  # good never changes ease
        assert new_state.repetitions == 4

    def test_hard_multiplies_interval_by_1_2_and_lowers_ease(self):
        state = new_card(ease_factor=2.4, interval_days=10, repetitions=3)
        new_state = schedule(state, "hard", NOW)
        assert new_state.interval_days == 12  # round(10 * 1.2)
        assert new_state.ease_factor == pytest.approx(2.25)

    def test_easy_multiplies_the_good_interval_by_1_3_and_raises_ease(self):
        state = new_card(ease_factor=2.4, interval_days=10, repetitions=3)
        new_state = schedule(state, "easy", NOW)
        assert new_state.interval_days == 31  # round(round(10 * 2.4) * 1.3) == round(31.2)
        assert new_state.ease_factor == pytest.approx(2.55)

    def test_due_at_is_now_plus_interval_days(self):
        state = new_card(ease_factor=2.4, interval_days=10, repetitions=3)
        new_state = schedule(state, "good", NOW)
        assert new_state.due_at == NOW + timedelta(days=new_state.interval_days)


class TestEaseFloor:
    def test_again_floors_ease_at_1_3(self):
        state = new_card(ease_factor=1.35)
        new_state = schedule(state, "again", NOW)
        assert new_state.ease_factor == pytest.approx(EASE_FLOOR)

    def test_hard_floors_ease_at_1_3(self):
        state = new_card(ease_factor=1.4, repetitions=3, interval_days=5)
        new_state = schedule(state, "hard", NOW)
        assert new_state.ease_factor == pytest.approx(EASE_FLOOR)

    def test_repeated_again_never_drops_below_the_floor(self):
        state = new_card(ease_factor=EASE_FLOOR)
        new_state = schedule(state, "again", NOW)
        assert new_state.ease_factor == pytest.approx(EASE_FLOOR)


class TestIntervalCap:
    def test_good_interval_is_capped_at_365_days(self):
        state = new_card(ease_factor=2.5, interval_days=300, repetitions=5)
        new_state = schedule(state, "good", NOW)
        assert new_state.interval_days == INTERVAL_CAP_DAYS

    def test_easy_interval_is_capped_at_365_days(self):
        state = new_card(ease_factor=2.5, interval_days=300, repetitions=5)
        new_state = schedule(state, "easy", NOW)
        assert new_state.interval_days == INTERVAL_CAP_DAYS


class TestOrderingGuarantee:
    """hard <= good <= easy must hold for every rating button's preview, from any state."""

    @pytest.mark.parametrize(
        "state",
        [
            new_card(),  # brand-new card
            new_card(ease_factor=2.5, interval_days=1, repetitions=1),  # second review
            new_card(ease_factor=2.4, interval_days=10, repetitions=3),  # mature
            new_card(ease_factor=1.3, interval_days=50, repetitions=4),  # floor ease
            new_card(ease_factor=2.5, interval_days=300, repetitions=5),  # near the cap
            # An unusual history: a lone "easy" at repetitions==0 set interval_days=4, so the
            # *next* review enters repetitions==1 with an interval higher than good's fixed 3
            # — this is exactly the case that needs the clamp, not just the raw formulas.
            new_card(ease_factor=2.5, interval_days=4, repetitions=1),
        ],
    )
    def test_hard_le_good_le_easy(self, state: CardState):
        intervals = preview(state, NOW)
        assert intervals["hard"] <= intervals["good"] <= intervals["easy"]


class TestAgainAfterALapse:
    def test_resets_repetitions_and_increments_lapses(self):
        state = new_card(ease_factor=2.4, interval_days=30, repetitions=5, lapses=2)
        new_state = schedule(state, "again", NOW)
        assert new_state.repetitions == 0
        assert new_state.lapses == 3
        assert new_state.interval_days == 0
        assert new_state.due_at == NOW + timedelta(minutes=10)


class TestPreviewMatchesSchedule:
    @pytest.mark.parametrize(
        "state",
        [
            new_card(),
            new_card(ease_factor=2.5, interval_days=1, repetitions=1),
            new_card(ease_factor=2.4, interval_days=10, repetitions=3),
        ],
    )
    def test_preview_equals_the_interval_schedule_would_apply(self, state: CardState):
        previewed = preview(state, NOW)
        for rating in RATINGS:
            scheduled = schedule(state, rating, NOW)
            assert previewed[rating] == scheduled.interval_days

    def test_preview_never_mutates_the_input_state(self):
        state = new_card(ease_factor=2.4, interval_days=10, repetitions=3)
        preview(state, NOW)
        assert state == new_card(ease_factor=2.4, interval_days=10, repetitions=3)
