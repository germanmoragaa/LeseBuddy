import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from factories import make_user
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_clock
from app.main import app as fastapi_app
from app.models import Article, Flashcard, ReviewLog, User, VocabularyItem
from app.scripts.import_dictionary import import_dictionary

FIXTURE_PATH = str(Path(__file__).parent / "fixtures" / "dictionary" / "sample.jsonl")
VALID_PASSWORD = "correct horse battery staple"

# A fixed instant used as "now" for every test unless overridden - a Wednesday, so Monday
# (this week's start) and "yesterday"/"today" never land on the same calendar day by accident.
NOW = datetime(2026, 2, 11, 12, 0, 0, tzinfo=UTC)
assert NOW.isoweekday() == 3  # Wednesday - pins the fixture if the date above ever changes
TODAY = NOW.date()
MONDAY_THIS_WEEK = TODAY - timedelta(days=TODAY.isoweekday() - 1)


@pytest.fixture
def dictionary(db_session: Session) -> None:
    import_dictionary(FIXTURE_PATH, "test-version", db=db_session)


@pytest.fixture(autouse=True)
def _clear_clock_override():
    yield
    fastapi_app.dependency_overrides.pop(get_clock, None)


def _freeze_clock(now: datetime) -> None:
    fastapi_app.dependency_overrides[get_clock] = lambda: lambda: now


def _login_as(client: TestClient, db_session: Session, *, username: str, email: str) -> User:
    user = make_user(
        db_session, email=email, username=username, password=VALID_PASSWORD, email_verified=True
    )
    response = client.post(
        "/api/v1/auth/login", json={"identifier": username, "password": VALID_PASSWORD}
    )
    assert response.status_code == 200
    return user


def _create_article(client: TestClient, text: str) -> str:
    response = client.post("/api/v1/articles", json={"original_text": text})
    assert response.status_code == 201
    return response.json()["id"]


def _token_span(client: TestClient, article_id: str, text: str) -> tuple[int, int]:
    analysis = client.get(f"/api/v1/articles/{article_id}/analysis").json()
    for token in analysis["tokens"]:
        if token["text"] == text:
            return token["start"], token["end"]
    raise AssertionError(f"no token with text {text!r} in analysis")


def _save_word(client: TestClient, article_id: str, word: str) -> dict:
    start, end = _token_span(client, article_id, word)
    response = client.post(
        "/api/v1/vocabulary", json={"article_id": article_id, "start": start, "end": end}
    )
    assert response.status_code == 201
    return response.json()["item"]


def _set_vocabulary_created_at(db_session: Session, item_id: str, created_at: datetime) -> None:
    db_session.query(VocabularyItem).filter_by(id=uuid.UUID(item_id)).update(
        {"created_at": created_at}
    )
    db_session.commit()


def _add_review_log(
    db_session: Session,
    user: User,
    *,
    reviewed_at: datetime,
    rating: str = "good",
    previous_interval_days: int = 1,
    lemma: str = "Hund",
) -> None:
    db_session.add(
        ReviewLog(
            user_id=user.id,
            flashcard_id=None,
            lemma=lemma,
            rating=rating,
            reviewed_at=reviewed_at,
            previous_ease_factor=2.5,
            previous_interval_days=previous_interval_days,
            previous_due_at=reviewed_at,
            new_ease_factor=2.5,
            new_interval_days=previous_interval_days + 1,
            new_due_at=reviewed_at + timedelta(days=1),
            scheduler_version=1,
        )
    )
    db_session.commit()


def _get_overview(client: TestClient, tz: str = "UTC") -> dict:
    response = client.get("/api/v1/analytics/overview", params={"tz": tz})
    assert response.status_code == 200
    return response.json()


def _get_activity(client: TestClient, days: int = 7, tz: str = "UTC") -> dict:
    response = client.get("/api/v1/analytics/activity", params={"tz": tz, "days": days})
    assert response.status_code == 200
    return response.json()


class TestOverviewCounts:
    def test_words_saved_and_mature(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        _freeze_clock(NOW)
        article_id = _create_article(client, "Der Hund schläft. Das Buch liegt da.")
        hund = _save_word(client, article_id, "Hund")
        _save_word(client, article_id, "Buch")

        db_session.query(Flashcard).filter_by(vocabulary_item_id=uuid.UUID(hund["id"])).update(
            {"interval_days": 21}
        )
        db_session.commit()

        overview = _get_overview(client)
        assert overview["words_saved"] == 2
        assert overview["words_mature"] == 1

    def test_words_saved_this_week_boundary(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        # Hund's vocabulary row gets a real, server-generated created_at (the save endpoint
        # never goes through the injectable clock) - the frozen "now" used below must be
        # captured *after* that real write, or this falls into the exact trap this test is
        # guarding against.
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client, "Der Hund schläft. Das Buch liegt da.")
        _save_word(client, article_id, "Hund")
        buch = _save_word(client, article_id, "Buch")

        now = datetime.now(UTC)
        _freeze_clock(now)
        monday_this_week = now.date() - timedelta(days=now.date().isoweekday() - 1)
        # One second before this week's Monday - last week, must not be counted.
        last_week = datetime.combine(monday_this_week, datetime.min.time(), tzinfo=UTC) - timedelta(
            seconds=1
        )
        _set_vocabulary_created_at(db_session, buch["id"], last_week)

        overview = _get_overview(client)
        assert overview["words_saved"] == 2
        assert overview["words_saved_this_week"] == 1

    def test_reviews_today_and_this_week(self, client: TestClient, db_session: Session) -> None:
        user = _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        _freeze_clock(NOW)
        _add_review_log(db_session, user, reviewed_at=NOW)
        _add_review_log(db_session, user, reviewed_at=NOW - timedelta(days=1))  # still this week
        last_week = datetime.combine(MONDAY_THIS_WEEK, datetime.min.time(), tzinfo=UTC) - timedelta(
            hours=1
        )
        _add_review_log(db_session, user, reviewed_at=last_week)

        overview = _get_overview(client)
        assert overview["reviews_today"] == 1
        assert overview["reviews_this_week"] == 2

    def test_due_now_matches_reviews_summary(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        # Flashcard.due_at is also set from a real, uninjected clock at save time - freeze to
        # a "now" captured after the save, same reasoning as the test above.
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client, "Der Hund schläft.")
        _save_word(client, article_id, "Hund")
        _freeze_clock(datetime.now(UTC))

        overview = _get_overview(client)
        summary = client.get("/api/v1/reviews/summary").json()
        assert overview["due_now"] == summary["due_count"] == 1

    def test_texts_opened_this_week(self, client: TestClient, db_session: Session) -> None:
        # /open also stamps last_opened_at from the real, uninjected clock.
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        opened_this_week = _create_article(client, "Text A")
        client.post(f"/api/v1/articles/{opened_this_week}/open")
        opened_last_week = _create_article(client, "Text B")
        client.post(f"/api/v1/articles/{opened_last_week}/open")

        now = datetime.now(UTC)
        _freeze_clock(now)
        monday_this_week = now.date() - timedelta(days=now.date().isoweekday() - 1)
        last_week = datetime.combine(monday_this_week, datetime.min.time(), tzinfo=UTC) - timedelta(
            hours=1
        )
        db_session.query(Article).filter_by(id=uuid.UUID(opened_last_week)).update(
            {"last_opened_at": last_week}
        )
        db_session.commit()

        overview = _get_overview(client)
        assert overview["texts_opened_this_week"] == 1

    def test_ownership_isolation_between_users(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        _freeze_clock(NOW)
        article_id = _create_article(client, "Der Hund schläft.")
        _save_word(client, article_id, "Hund")
        client.post("/api/v1/auth/logout")

        _login_as(client, db_session, username="bailey_jones", email="bailey@example.com")
        overview = _get_overview(client)
        assert overview["words_saved"] == 0
        assert overview["due_now"] == 0


class TestStreak:
    def test_new_user_returns_zeros(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        _freeze_clock(NOW)

        overview = _get_overview(client)
        assert overview["streak"] == {
            "current_days": 0,
            "longest_days": 0,
            "last_7_days": [False] * 7,
        }
        assert overview["recommendation"]["type"] == "add_text"

    def test_streak_continues_from_yesterday_when_today_has_no_activity_yet(
        self, client: TestClient, db_session: Session
    ) -> None:
        user = _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        _freeze_clock(NOW)
        yesterday = NOW - timedelta(days=1)
        day_before = NOW - timedelta(days=2)
        _add_review_log(db_session, user, reviewed_at=yesterday)
        _add_review_log(db_session, user, reviewed_at=day_before)

        overview = _get_overview(client)
        assert overview["streak"]["current_days"] == 2
        assert overview["streak"]["last_7_days"][-1] is False  # today: no activity yet
        assert overview["streak"]["last_7_days"][-2] is True  # yesterday

    def test_streak_broken_by_a_gap_day(self, client: TestClient, db_session: Session) -> None:
        user = _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        _freeze_clock(NOW)
        # Active 3 days ago, then a gap (2 days ago and yesterday are both inactive), nothing
        # today either.
        _add_review_log(db_session, user, reviewed_at=NOW - timedelta(days=3))

        overview = _get_overview(client)
        assert overview["streak"]["current_days"] == 0
        assert overview["streak"]["longest_days"] == 1

    def test_longest_streak_survives_after_it_ends(
        self, client: TestClient, db_session: Session
    ) -> None:
        user = _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        _freeze_clock(NOW)
        for days_ago in (10, 9, 8):
            _add_review_log(db_session, user, reviewed_at=NOW - timedelta(days=days_ago))
        # Isolated, more recent activity - a separate, shorter run.
        _add_review_log(db_session, user, reviewed_at=NOW - timedelta(days=4))

        overview = _get_overview(client)
        assert overview["streak"]["longest_days"] == 3
        assert overview["streak"]["current_days"] == 0


class TestRecommendation:
    def test_review_when_cards_are_due(
        self, client: TestClient, db_session: Session, dictionary: None
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client, "Der Hund schläft.")
        _save_word(client, article_id, "Hund")
        # Flashcard.due_at is real-clock-stamped at save time - freeze to "now" captured
        # afterwards so the card actually reads as due.
        _freeze_clock(datetime.now(UTC))

        overview = _get_overview(client)
        assert overview["recommendation"]["type"] == "review"
        assert "1" in overview["recommendation"]["reason"]

    def test_continue_reading_when_nothing_due_but_an_article_is_unfinished(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        _freeze_clock(NOW)
        article_id = _create_article(client, "Ein kurzer Text zum Lesen.")
        client.patch(f"/api/v1/articles/{article_id}/position", json={"offset": 5})

        overview = _get_overview(client)
        assert overview["recommendation"]["type"] == "continue_reading"
        assert overview["recommendation"]["article_id"] == article_id

    def test_add_text_when_everything_is_already_read(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        _freeze_clock(NOW)
        text = "Ein kurzer Text."
        article_id = _create_article(client, text)
        client.patch(f"/api/v1/articles/{article_id}/position", json={"offset": len(text)})

        overview = _get_overview(client)
        assert overview["recommendation"]["type"] == "add_text"


class TestActivity:
    def test_per_day_series_and_cumulative_vocabulary(
        self, client: TestClient, db_session: Session
    ) -> None:
        user = _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        _freeze_clock(NOW)

        before_range = NOW - timedelta(days=10)
        db_session.add(
            VocabularyItem(
                user_id=user.id,
                lemma="Vorher",
                display_form="Vorher",
                part_of_speech="NOUN",
            )
        )
        db_session.commit()
        baseline_item = db_session.query(VocabularyItem).filter_by(lemma="Vorher").one()
        _set_vocabulary_created_at(db_session, str(baseline_item.id), before_range)

        db_session.add(
            VocabularyItem(
                user_id=user.id, lemma="Heute", display_form="Heute", part_of_speech="NOUN"
            )
        )
        db_session.commit()
        today_item = db_session.query(VocabularyItem).filter_by(lemma="Heute").one()
        _set_vocabulary_created_at(db_session, str(today_item.id), NOW)

        _add_review_log(db_session, user, reviewed_at=NOW)
        _add_review_log(db_session, user, reviewed_at=NOW)

        activity = _get_activity(client, days=7)
        assert len(activity["days"]) == 7
        today_point = activity["days"][-1]
        assert today_point["date"] == str(TODAY)
        assert today_point["reviews"] == 2
        assert today_point["words_saved"] == 1
        # Baseline (1, created 10 days before the 7-day range) + today's 1 new word.
        assert today_point["cumulative_vocabulary"] == 2

    def test_rating_breakdown_and_retention_excludes_new_cards(
        self, client: TestClient, db_session: Session
    ) -> None:
        user = _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        _freeze_clock(NOW)
        # A brand-new card's first review (previous_interval_days == 0) never counts toward
        # retention, whatever its rating.
        _add_review_log(db_session, user, reviewed_at=NOW, rating="good", previous_interval_days=0)
        # Two reviews of cards that already had a real interval - one retained, one lapsed.
        _add_review_log(db_session, user, reviewed_at=NOW, rating="good", previous_interval_days=3)
        _add_review_log(db_session, user, reviewed_at=NOW, rating="again", previous_interval_days=3)
        # Outside the 7-day range entirely - must not affect the breakdown.
        _add_review_log(
            db_session,
            user,
            reviewed_at=NOW - timedelta(days=30),
            rating="easy",
            previous_interval_days=3,
        )

        activity = _get_activity(client, days=7)
        assert activity["rating_counts"] == {"again": 1, "hard": 0, "good": 2, "easy": 0}
        assert activity["rating_percentages"]["good"] == pytest.approx(200 / 3)
        assert activity["retention_percent"] == pytest.approx(50.0)

    def test_retention_is_null_with_no_eligible_reviews(
        self, client: TestClient, db_session: Session
    ) -> None:
        user = _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        _freeze_clock(NOW)
        _add_review_log(db_session, user, reviewed_at=NOW, previous_interval_days=0)

        activity = _get_activity(client, days=7)
        assert activity["retention_percent"] is None

    def test_days_param_controls_series_length(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        _freeze_clock(NOW)

        assert len(_get_activity(client, days=30)["days"]) == 30
        assert len(_get_activity(client, days=90)["days"]) == 90

    def test_review_near_midnight_is_attributed_to_the_correct_local_day(
        self, client: TestClient, db_session: Session
    ) -> None:
        """23:15 UTC on day X is already past midnight (00:15) in Europe/Berlin (UTC+1 in
        winter) - it must be attributed to local day X+1, not UTC day X."""
        user = _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        now_berlin_morning = datetime(2026, 2, 12, 9, 0, tzinfo=UTC)
        _freeze_clock(now_berlin_morning)
        just_before_midnight_utc = datetime(2026, 2, 11, 23, 15, tzinfo=UTC)
        _add_review_log(db_session, user, reviewed_at=just_before_midnight_utc)

        activity = _get_activity(client, days=7, tz="Europe/Berlin")
        by_date = {day["date"]: day["reviews"] for day in activity["days"]}
        assert by_date["2026-02-12"] == 1
        assert by_date.get("2026-02-11", 0) == 0


class TestAuthAndValidation:
    def test_unverified_user_gets_403(self, client: TestClient, db_session: Session) -> None:
        make_user(
            db_session, email="alex@example.com", username="alex_morgan", password=VALID_PASSWORD
        )
        client.post(
            "/api/v1/auth/login", json={"identifier": "alex_morgan", "password": VALID_PASSWORD}
        )

        assert client.get("/api/v1/analytics/overview").status_code == 403
        assert client.get("/api/v1/analytics/activity").status_code == 403

    def test_invalid_timezone_gets_422(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")

        response = client.get("/api/v1/analytics/overview", params={"tz": "Not/AZone"})

        assert response.status_code == 422
