from datetime import UTC, datetime, timedelta

import pytest
from factories import make_user
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import generate_session_token, hash_token, verify_password
from app.models import User, UserSession
from app.services import auth_service
from app.services.auth_service import LOCKOUT_THRESHOLD

VALID_PASSWORD = "correct horse battery staple"


def _register(client: TestClient, **overrides: str):
    payload = {
        "username": "alex_morgan",
        "email": "alex@example.com",
        "password": VALID_PASSWORD,
    }
    payload.update(overrides)
    return client.post("/api/v1/auth/register", json=payload)


def _make_alex(db_session: Session) -> User:
    return make_user(
        db_session, email="alex@example.com", username="alex_morgan", password=VALID_PASSWORD
    )


class TestRegister:
    def test_success_creates_user_and_session(
        self, client: TestClient, db_session: Session
    ) -> None:
        response = _register(client)

        assert response.status_code == 201
        body = response.json()
        assert body["username"] == "alex_morgan"
        assert body["email"] == "alex@example.com"
        assert body["email_verified"] is False

        stored = db_session.query(User).filter_by(email="alex@example.com").one()
        assert stored.password_hash != VALID_PASSWORD
        assert verify_password(VALID_PASSWORD, stored.password_hash)
        assert stored.email_verified_at is None

        set_cookie = response.headers.get("set-cookie", "")
        assert "session_token=" in set_cookie
        assert "httponly" in set_cookie.lower()
        assert "samesite=lax" in set_cookie.lower()
        assert "path=/" in set_cookie.lower()
        assert "secure" not in set_cookie.lower()

    def test_duplicate_username_case_insensitive(self, client: TestClient) -> None:
        _register(client, username="Alex_Morgan", email="first@example.com")

        response = _register(client, username="alex_morgan", email="second@example.com")

        assert response.status_code == 409
        assert response.json()["detail"][0]["loc"] == ["body", "username"]

    def test_duplicate_email_case_insensitive(self, client: TestClient) -> None:
        _register(client, username="first_user", email="shared@example.com")

        response = _register(client, username="second_user", email="SHARED@Example.com")

        assert response.status_code == 409
        assert response.json()["detail"][0]["loc"] == ["body", "email"]

    def test_invalid_username_rejected(self, client: TestClient) -> None:
        response = _register(client, username="ab")

        assert response.status_code == 422

    def test_invalid_email_rejected(self, client: TestClient) -> None:
        response = _register(client, email="not-an-email")

        assert response.status_code == 422

    def test_invalid_password_rejected(self, client: TestClient) -> None:
        response = _register(client, password="short")

        assert response.status_code == 422

    def test_concurrent_registration_maps_integrity_error_to_409(
        self, client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The real guarantee against duplicate usernames is the DB's unique index, not the
        pre-check — if two requests race past the pre-check (as the patch below forces),
        the commit's IntegrityError must still map to a 409, never an unhandled 500."""
        _make_alex(db_session)
        db_session.commit()  # must survive the rollback below, not just the flush
        real_find_by_username = auth_service._find_user_by_username
        calls = {"n": 0}

        def flaky_find_by_username(db: Session, username: str) -> User | None:
            calls["n"] += 1
            if calls["n"] == 1:
                return None
            return real_find_by_username(db, username)

        monkeypatch.setattr(auth_service, "_find_user_by_username", flaky_find_by_username)

        response = _register(client, username="alex_morgan", email="different@example.com")

        assert response.status_code == 409
        assert response.json()["detail"][0]["loc"] == ["body", "username"]

    def test_concurrent_registration_maps_email_integrity_error_to_409(
        self, client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _make_alex(db_session)
        db_session.commit()  # must survive the rollback below, not just the flush
        real_find_by_email = auth_service._find_user_by_email
        calls = {"n": 0}

        def flaky_find_by_email(db: Session, email: str) -> User | None:
            calls["n"] += 1
            if calls["n"] == 1:
                return None
            return real_find_by_email(db, email)

        monkeypatch.setattr(auth_service, "_find_user_by_email", flaky_find_by_email)

        response = _register(client, username="different_user", email="alex@example.com")

        assert response.status_code == 409
        assert response.json()["detail"][0]["loc"] == ["body", "email"]


class TestLogin:
    def test_login_with_email(self, client: TestClient, db_session: Session) -> None:
        _make_alex(db_session)

        response = client.post(
            "/api/v1/auth/login",
            json={"identifier": "alex@example.com", "password": VALID_PASSWORD},
        )

        assert response.status_code == 200
        assert response.json()["username"] == "alex_morgan"
        assert "session_token=" in response.headers.get("set-cookie", "")

    def test_login_with_username(self, client: TestClient, db_session: Session) -> None:
        _make_alex(db_session)

        response = client.post(
            "/api/v1/auth/login",
            json={"identifier": "alex_morgan", "password": VALID_PASSWORD},
        )

        assert response.status_code == 200
        assert response.json()["username"] == "alex_morgan"

    def test_wrong_password_and_unknown_user_return_identical_response(
        self, client: TestClient, db_session: Session
    ) -> None:
        _make_alex(db_session)

        wrong_password = client.post(
            "/api/v1/auth/login",
            json={"identifier": "alex_morgan", "password": "incorrect-password"},
        )
        unknown_user = client.post(
            "/api/v1/auth/login",
            json={"identifier": "nobody-registered", "password": "incorrect-password"},
        )

        assert wrong_password.status_code == unknown_user.status_code == 401
        assert wrong_password.json() == unknown_user.json()

    def test_lockout_after_too_many_failed_attempts(
        self, client: TestClient, db_session: Session
    ) -> None:
        _make_alex(db_session)

        for _ in range(LOCKOUT_THRESHOLD):
            response = client.post(
                "/api/v1/auth/login",
                json={"identifier": "alex_morgan", "password": "incorrect-password"},
            )
            assert response.status_code == 401

        locked_out = client.post(
            "/api/v1/auth/login",
            json={"identifier": "alex_morgan", "password": VALID_PASSWORD},
        )

        assert locked_out.status_code == 429


class TestLogout:
    def test_logout_invalidates_session(self, client: TestClient, db_session: Session) -> None:
        _make_alex(db_session)
        client.post(
            "/api/v1/auth/login",
            json={"identifier": "alex_morgan", "password": VALID_PASSWORD},
        )
        assert client.get("/api/v1/me").status_code == 200

        logout_response = client.post("/api/v1/auth/logout")
        assert logout_response.status_code == 204

        assert client.get("/api/v1/me").status_code == 401


class TestMe:
    def test_without_session_returns_401(self, client: TestClient) -> None:
        response = client.get("/api/v1/me")

        assert response.status_code == 401

    def test_with_valid_session_returns_user(self, client: TestClient, db_session: Session) -> None:
        _make_alex(db_session)
        client.post(
            "/api/v1/auth/login",
            json={"identifier": "alex_morgan", "password": VALID_PASSWORD},
        )

        response = client.get("/api/v1/me")

        assert response.status_code == 200
        assert response.json()["username"] == "alex_morgan"

    def test_with_expired_session_returns_401(
        self, client: TestClient, db_session: Session
    ) -> None:
        user = _make_alex(db_session)
        raw_token = generate_session_token()
        db_session.add(
            UserSession(
                user_id=user.id,
                token_hash=hash_token(raw_token),
                expires_at=datetime.now(UTC) - timedelta(days=1),
            )
        )
        db_session.commit()
        client.cookies.set("session_token", raw_token)

        response = client.get("/api/v1/me")

        assert response.status_code == 401
