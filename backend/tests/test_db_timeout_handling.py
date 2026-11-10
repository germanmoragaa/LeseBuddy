"""Verifies app/main.py's OperationalError handler — a cancelled query (the app engine's own
statement_timeout/lock_timeout firing, most likely because some other session holds a lock on
the rows being read) must surface as a clean, typed JSON error, never a 500 with a raw stack
trace. See app/core/db.py and the incident that prompted both.
"""

from collections.abc import Callable

import pytest
from factories import make_user
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

VALID_PASSWORD = "correct horse battery staple"


class _FakeOrig(Exception):
    """Stands in for the real psycopg exception OperationalError.orig would hold — only the
    `.sqlstate` attribute the handler reads actually matters here."""

    def __init__(self, sqlstate: str) -> None:
        super().__init__(f"simulated Postgres error {sqlstate}")
        self.sqlstate = sqlstate


def _login_as(client: TestClient, db_session: Session, *, username: str, email: str) -> None:
    make_user(
        db_session, email=email, username=username, password=VALID_PASSWORD, email_verified=True
    )
    response = client.post(
        "/api/v1/auth/login", json={"identifier": username, "password": VALID_PASSWORD}
    )
    assert response.status_code == 200


def _raise_operational_error(sqlstate: str) -> Callable[..., None]:
    def _raise(*args: object, **kwargs: object) -> None:
        raise OperationalError("SELECT 1", {}, _FakeOrig(sqlstate))

    return _raise


class TestOperationalErrorHandling:
    def test_lock_timeout_maps_to_a_clean_503(
        self, client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        monkeypatch.setattr(
            "app.api.articles.list_articles_for_user", _raise_operational_error("55P03")
        )

        response = client.get("/api/v1/articles")

        assert response.status_code == 503
        assert response.json() == {
            "detail": {
                "code": "database_busy",
                "message": "The database is busy right now. Please try again.",
            }
        }

    def test_statement_timeout_maps_to_a_clean_504(
        self, client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        monkeypatch.setattr(
            "app.api.articles.list_articles_for_user", _raise_operational_error("57014")
        )

        response = client.get("/api/v1/articles")

        assert response.status_code == 504
        assert response.json() == {
            "detail": {
                "code": "database_timeout",
                "message": "That request took too long. Please try again.",
            }
        }

    def test_other_operational_errors_map_to_a_clean_503_without_a_stack_trace(
        self, client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        monkeypatch.setattr(
            "app.api.articles.list_articles_for_user", _raise_operational_error("08006")
        )

        response = client.get("/api/v1/articles")

        assert response.status_code == 503
        body = response.json()
        assert body["detail"]["code"] == "database_unavailable"
        # No raw exception text/traceback anywhere in the response body.
        assert "Traceback" not in response.text
        assert "simulated Postgres error" not in response.text
