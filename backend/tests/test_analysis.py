import time

from factories import make_user
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import ArticleAnalysis
from app.services import analysis_service

VALID_PASSWORD = "correct horse battery staple"
SAMPLE_TEXT = "Ich rufe dich morgen an. Der Zug fährt um acht ab."


def _login_as(client: TestClient, db_session: Session, *, username: str, email: str) -> None:
    make_user(
        db_session, email=email, username=username, password=VALID_PASSWORD, email_verified=True
    )
    response = client.post(
        "/api/v1/auth/login", json={"identifier": username, "password": VALID_PASSWORD}
    )
    assert response.status_code == 200


def _create_article(client: TestClient, *, original_text: str = SAMPLE_TEXT) -> str:
    response = client.post("/api/v1/articles", json={"original_text": original_text})
    assert response.status_code == 201
    return response.json()["id"]


class TestGetAnalysis:
    def test_computes_and_returns_analysis(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client)

        response = client.get(f"/api/v1/articles/{article_id}/analysis")

        assert response.status_code == 200
        body = response.json()
        assert body["analysis_version"] == analysis_service.CURRENT_ANALYSIS_VERSION
        assert body["difficulty_estimate"] is None
        assert len(body["tokens"]) > 0
        assert len(body["sentences"]) == 2
        assert len(body["separable_verbs"]) == 2

    def test_second_request_reuses_the_stored_row(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client)

        first = client.get(f"/api/v1/articles/{article_id}/analysis")
        assert first.status_code == 200

        rows_after_first = db_session.query(ArticleAnalysis).filter_by(article_id=article_id).all()
        assert len(rows_after_first) == 1
        stored_id = rows_after_first[0].id

        second = client.get(f"/api/v1/articles/{article_id}/analysis")
        assert second.status_code == 200
        assert second.json() == first.json()

        rows_after_second = db_session.query(ArticleAnalysis).filter_by(article_id=article_id).all()
        assert len(rows_after_second) == 1
        assert rows_after_second[0].id == stored_id

    def test_recomputed_when_analysis_version_bumps(
        self, client: TestClient, db_session: Session, monkeypatch
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client)

        first = client.get(f"/api/v1/articles/{article_id}/analysis")
        assert first.json()["analysis_version"] == 1

        monkeypatch.setattr(analysis_service, "CURRENT_ANALYSIS_VERSION", 2)

        second = client.get(f"/api/v1/articles/{article_id}/analysis")
        assert second.status_code == 200
        assert second.json()["analysis_version"] == 2

        rows = db_session.query(ArticleAnalysis).filter_by(article_id=article_id).all()
        assert {row.analysis_version for row in rows} == {1, 2}

    def test_other_user_gets_404(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client)
        client.post("/api/v1/auth/logout")

        _login_as(client, db_session, username="bailey_jones", email="bailey@example.com")
        response = client.get(f"/api/v1/articles/{article_id}/analysis")

        assert response.status_code == 404

    def test_unverified_user_gets_403(self, client: TestClient, db_session: Session) -> None:
        make_user(
            db_session, email="alex@example.com", username="alex_morgan", password=VALID_PASSWORD
        )
        client.post(
            "/api/v1/auth/login",
            json={"identifier": "alex_morgan", "password": VALID_PASSWORD},
        )

        response = client.get("/api/v1/articles/00000000-0000-0000-0000-000000000000/analysis")

        assert response.status_code == 403

    def test_unknown_article_gets_404(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")

        response = client.get("/api/v1/articles/00000000-0000-0000-0000-000000000000/analysis")

        assert response.status_code == 404


class TestAnalysisPerformanceNote:
    """Not an assertion-bearing test — records measured compute time/payload size for a
    realistically long text, so the numbers in docs/decisions/0003-nlp-pipeline.md are backed
    by something reproducible rather than asserted blind."""

    def test_measure_time_and_payload_size_for_a_long_text(
        self, client: TestClient, db_session: Session, capsys
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        long_text = ("Die Katze schläft auf dem Sofa, während der Hund im Garten spielt. " * 400)[
            :49_999
        ]
        article_id = _create_article(client, original_text=long_text)

        started = time.perf_counter()
        response = client.get(f"/api/v1/articles/{article_id}/analysis")
        elapsed = time.perf_counter() - started

        assert response.status_code == 200
        payload_bytes = len(response.content)
        with capsys.disabled():
            print(
                f"\n[analysis perf] {len(long_text)} chars -> {elapsed:.2f}s, "
                f"{payload_bytes / 1024:.1f} KiB response"
            )
