import re
from datetime import UTC, datetime, timedelta

import pytest
from factories import make_user
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_email_sender
from app.core.config import get_settings
from app.core.db import get_db
from app.main import app
from app.models import EmailVerificationCode, User
from app.services.email import EmailMessage, FakeEmailSender

VALID_PASSWORD = "correct horse battery staple"
CODE_PATTERN = re.compile(r"\b(\d{6})\b")


def _register(client: TestClient, **overrides: str):
    payload = {
        "username": "alex_morgan",
        "email": "alex@example.com",
        "password": VALID_PASSWORD,
    }
    payload.update(overrides)
    return client.post("/api/v1/auth/register", json=payload)


def _latest_code(fake_email_sender: FakeEmailSender) -> str:
    match = CODE_PATTERN.search(fake_email_sender.sent[-1].text_body)
    assert match is not None
    return match.group(1)


def _register_and_get_code(
    client: TestClient, fake_email_sender: FakeEmailSender, **overrides: str
) -> str:
    response = _register(client, **overrides)
    assert response.status_code == 201
    return _latest_code(fake_email_sender)


class TestRegistrationSendsCode:
    def test_sends_code_to_registered_email(
        self, client: TestClient, fake_email_sender: FakeEmailSender
    ) -> None:
        _register(client)

        assert len(fake_email_sender.sent) == 1
        assert fake_email_sender.sent[0].to == "alex@example.com"
        assert CODE_PATTERN.search(fake_email_sender.sent[0].text_body) is not None

    def test_registration_succeeds_even_if_sending_fails(self, db_session: Session) -> None:
        class FailingEmailSender:
            def send(self, message: EmailMessage) -> None:
                raise RuntimeError("SMTP is unreachable")

        def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_email_sender] = lambda: FailingEmailSender()
        try:
            with TestClient(app) as client:
                response = _register(client)
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 201
        assert response.json()["email_verified"] is False


class TestVerifyEmail:
    def test_correct_code_verifies(
        self, client: TestClient, fake_email_sender: FakeEmailSender
    ) -> None:
        code = _register_and_get_code(client, fake_email_sender)

        response = client.post("/api/v1/auth/verify-email", json={"code": code})

        assert response.status_code == 200
        assert response.json()["email_verified"] is True

    def test_verifying_twice_is_idempotent(
        self, client: TestClient, fake_email_sender: FakeEmailSender
    ) -> None:
        code = _register_and_get_code(client, fake_email_sender)
        client.post("/api/v1/auth/verify-email", json={"code": code})

        response = client.post("/api/v1/auth/verify-email", json={"code": code})

        assert response.status_code == 200
        assert response.json()["email_verified"] is True

    def test_wrong_code_rejected(
        self, client: TestClient, fake_email_sender: FakeEmailSender
    ) -> None:
        correct_code = _register_and_get_code(client, fake_email_sender)
        wrong_code = "000000" if correct_code != "000000" else "111111"

        response = client.post("/api/v1/auth/verify-email", json={"code": wrong_code})

        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "invalid_code"

    def test_expired_code_rejected(
        self,
        client: TestClient,
        fake_email_sender: FakeEmailSender,
        db_session: Session,
    ) -> None:
        code = _register_and_get_code(client, fake_email_sender)
        db_session.query(EmailVerificationCode).update(
            {"expires_at": datetime.now(UTC) - timedelta(minutes=1)}
        )
        db_session.commit()

        response = client.post("/api/v1/auth/verify-email", json={"code": code})

        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "code_expired"

    def test_no_active_code_rejected(self, client: TestClient, db_session: Session) -> None:
        user = make_user(db_session, email="alex@example.com", username="alex_morgan")
        client.post(
            "/api/v1/auth/login",
            json={"identifier": "alex_morgan", "password": VALID_PASSWORD},
        )

        response = client.post("/api/v1/auth/verify-email", json={"code": "123456"})

        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "no_active_code"
        assert user.email_verified_at is None

    def test_max_attempts_exhausted_then_blocked(
        self, client: TestClient, fake_email_sender: FakeEmailSender
    ) -> None:
        correct_code = _register_and_get_code(client, fake_email_sender)
        wrong_code = "000000" if correct_code != "000000" else "111111"
        max_attempts = get_settings().verification_code_max_attempts

        for _ in range(max_attempts):
            response = client.post("/api/v1/auth/verify-email", json={"code": wrong_code})
            assert response.json()["detail"]["code"] == "invalid_code"

        blocked = client.post("/api/v1/auth/verify-email", json={"code": correct_code})

        assert blocked.status_code == 400
        assert blocked.json()["detail"]["code"] == "too_many_attempts"


class TestResendVerification:
    def test_resend_before_cooldown_is_rate_limited(
        self, client: TestClient, fake_email_sender: FakeEmailSender
    ) -> None:
        _register_and_get_code(client, fake_email_sender)

        response = client.post("/api/v1/auth/resend-verification")

        assert response.status_code == 429
        assert response.json()["detail"]["code"] == "resend_cooldown"
        assert response.json()["detail"]["retry_after"] > 0

    def test_resend_issues_new_code_that_invalidates_old_one(
        self,
        client: TestClient,
        fake_email_sender: FakeEmailSender,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        old_code = _register_and_get_code(client, fake_email_sender)
        monkeypatch.setattr(get_settings(), "verification_resend_cooldown_seconds", 0)

        resend_response = client.post("/api/v1/auth/resend-verification")
        assert resend_response.status_code == 204
        new_code = _latest_code(fake_email_sender)
        assert new_code != old_code

        stale_attempt = client.post("/api/v1/auth/verify-email", json={"code": old_code})
        assert stale_attempt.status_code == 400
        assert stale_attempt.json()["detail"]["code"] == "invalid_code"

        fresh_attempt = client.post("/api/v1/auth/verify-email", json={"code": new_code})
        assert fresh_attempt.status_code == 200
        assert fresh_attempt.json()["email_verified"] is True

    def test_resend_hourly_cap(
        self,
        client: TestClient,
        fake_email_sender: FakeEmailSender,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _register_and_get_code(client, fake_email_sender)  # code #1, via registration
        monkeypatch.setattr(get_settings(), "verification_resend_cooldown_seconds", 0)
        hourly_cap = get_settings().verification_resend_hourly_cap

        for _ in range(hourly_cap - 1):  # codes #2..#hourly_cap
            response = client.post("/api/v1/auth/resend-verification")
            assert response.status_code == 204

        capped = client.post("/api/v1/auth/resend-verification")

        assert capped.status_code == 429
        assert capped.json()["detail"]["code"] == "resend_hourly_cap"
        assert capped.json()["detail"]["retry_after"] > 0

    def test_resend_when_already_verified_is_a_no_op(
        self, client: TestClient, fake_email_sender: FakeEmailSender
    ) -> None:
        code = _register_and_get_code(client, fake_email_sender)
        client.post("/api/v1/auth/verify-email", json={"code": code})
        sent_before = len(fake_email_sender.sent)

        response = client.post("/api/v1/auth/resend-verification")

        assert response.status_code == 204
        assert len(fake_email_sender.sent) == sent_before


class TestArticlesRequireVerification:
    def test_unverified_user_gets_403(
        self, client: TestClient, fake_email_sender: FakeEmailSender
    ) -> None:
        _register_and_get_code(client, fake_email_sender)

        response = client.get("/api/v1/articles")

        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "email_not_verified"

    def test_verified_user_gets_200(
        self, client: TestClient, fake_email_sender: FakeEmailSender
    ) -> None:
        code = _register_and_get_code(client, fake_email_sender)
        client.post("/api/v1/auth/verify-email", json={"code": code})

        response = client.get("/api/v1/articles")

        assert response.status_code == 200
        assert response.json() == []


class TestEmailUniquenessIsDbEnforced:
    def test_duplicate_username_rejected_case_insensitively_at_db_level(
        self, db_session: Session
    ) -> None:
        make_user(db_session, email="first@example.com", username="alex_morgan")

        with pytest.raises(IntegrityError):
            make_user(db_session, email="second@example.com", username="ALEX_MORGAN")

    def test_duplicate_email_rejected_case_insensitively_at_db_level(
        self, db_session: Session
    ) -> None:
        make_user(db_session, email="shared@example.com", username="first_user")

        with pytest.raises(IntegrityError):
            make_user(db_session, email="SHARED@example.com", username="second_user")


class TestUnverifiedAccountExpiry:
    def test_expired_unverified_account_frees_its_username_and_email(
        self, client: TestClient, db_session: Session
    ) -> None:
        stale_cutoff_hours = get_settings().unverified_account_ttl_hours
        make_user(
            db_session,
            email="alex@example.com",
            username="alex_morgan",
            email_verified=False,
            created_at=datetime.now(UTC) - timedelta(hours=stale_cutoff_hours, minutes=1),
        )

        response = _register(client)

        assert response.status_code == 201
        assert db_session.query(User).filter_by(email="alex@example.com").count() == 1

    def test_non_expired_unverified_account_still_blocks_registration(
        self, client: TestClient, db_session: Session
    ) -> None:
        make_user(
            db_session,
            email="alex@example.com",
            username="alex_morgan",
            email_verified=False,
        )

        response = _register(client)

        assert response.status_code == 409

    def test_expired_account_cleanup_cascades_sessions_and_codes(
        self, client: TestClient, db_session: Session, fake_email_sender: FakeEmailSender
    ) -> None:
        stale_cutoff_hours = get_settings().unverified_account_ttl_hours
        stale_user = make_user(
            db_session,
            email="alex@example.com",
            username="alex_morgan",
            email_verified=False,
            created_at=datetime.now(UTC) - timedelta(hours=stale_cutoff_hours, minutes=1),
        )
        stale_user_id = stale_user.id
        db_session.add(
            EmailVerificationCode(
                user_id=stale_user_id,
                code_hash="irrelevant",
                expires_at=datetime.now(UTC) + timedelta(minutes=15),
            )
        )
        db_session.commit()

        response = _register(client)

        assert response.status_code == 201
        assert db_session.get(User, stale_user_id) is None
        assert db_session.query(EmailVerificationCode).filter_by(user_id=stale_user_id).count() == 0
