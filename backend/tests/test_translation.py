from factories import make_user
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api import deps
from app.core.config import get_settings
from app.main import app
from app.models import TranslationCache, TranslationRequestLog
from app.services.translation.fake_provider import FakeTranslationProvider
from app.services.translation.provider import (
    NullTranslationProvider,
    TranslationProviderError,
    TranslationTimeoutError,
    UsageSnapshot,
)

VALID_PASSWORD = "correct horse battery staple"
SAMPLE_TEXT = "Ich rufe dich morgen an. Der Hund schläft."


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


def _token_span(client: TestClient, article_id: str, text: str) -> tuple[int, int]:
    analysis = client.get(f"/api/v1/articles/{article_id}/analysis").json()
    for token in analysis["tokens"]:
        if token["text"] == text:
            return token["start"], token["end"]
    raise AssertionError(f"no token with text {text!r} in analysis")


class TestTranslateSelection:
    def test_translates_selection_with_fake_provider(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client)
        start, end = _token_span(client, article_id, "Hund")

        response = client.post(
            f"/api/v1/articles/{article_id}/translate", json={"start": start, "end": end}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["selection_translation"] == "[EN-US] Hund"
        assert body["sentence_translation"] is None
        assert body["source"] == "machine_translation"

    def test_includes_sentence_translation_on_request(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client)
        start, end = _token_span(client, article_id, "Hund")

        response = client.post(
            f"/api/v1/articles/{article_id}/translate",
            json={"start": start, "end": end, "include_sentence": True},
        )

        assert response.status_code == 200
        assert response.json()["sentence_translation"] == "[EN-US] Der Hund schläft."

    def test_missing_key_returns_clear_error(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client)
        start, end = _token_span(client, article_id, "Hund")

        app.dependency_overrides[deps.get_translation_provider] = lambda: NullTranslationProvider()
        response = client.post(
            f"/api/v1/articles/{article_id}/translate", json={"start": start, "end": end}
        )

        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "translation_not_configured"

    def test_timeout_returns_504(
        self,
        client: TestClient,
        db_session: Session,
        fake_translation_provider: FakeTranslationProvider,
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client)
        start, end = _token_span(client, article_id, "Hund")
        fake_translation_provider.fail_with = TranslationTimeoutError()

        response = client.post(
            f"/api/v1/articles/{article_id}/translate", json={"start": start, "end": end}
        )

        assert response.status_code == 504
        assert response.json()["detail"]["code"] == "translation_timeout"

    def test_provider_error_returns_502(
        self,
        client: TestClient,
        db_session: Session,
        fake_translation_provider: FakeTranslationProvider,
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client)
        start, end = _token_span(client, article_id, "Hund")
        fake_translation_provider.fail_with = TranslationProviderError()

        response = client.post(
            f"/api/v1/articles/{article_id}/translate", json={"start": start, "end": end}
        )

        assert response.status_code == 502
        assert response.json()["detail"]["code"] == "translation_provider_error"

    def test_quota_exhausted_blocks_before_calling_provider(
        self,
        client: TestClient,
        db_session: Session,
        fake_translation_provider: FakeTranslationProvider,
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client)
        start, end = _token_span(client, article_id, "Hund")
        fake_translation_provider.usage = UsageSnapshot(
            characters_used=500_000, character_limit=500_000
        )

        response = client.post(
            f"/api/v1/articles/{article_id}/translate", json={"start": start, "end": end}
        )

        assert response.status_code == 429
        assert response.json()["detail"]["code"] == "translation_quota_exceeded"
        assert fake_translation_provider.calls == []

    def test_quota_warning_near_limit_still_succeeds(
        self,
        client: TestClient,
        db_session: Session,
        fake_translation_provider: FakeTranslationProvider,
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client)
        start, end = _token_span(client, article_id, "Hund")
        fake_translation_provider.usage = UsageSnapshot(
            characters_used=480_000, character_limit=500_000
        )

        response = client.post(
            f"/api/v1/articles/{article_id}/translate", json={"start": start, "end": end}
        )

        assert response.status_code == 200
        assert response.json()["quota_warning"] is not None

    def test_cache_hit_does_not_call_provider_again(
        self,
        client: TestClient,
        db_session: Session,
        fake_translation_provider: FakeTranslationProvider,
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client)
        start, end = _token_span(client, article_id, "Hund")

        first = client.post(
            f"/api/v1/articles/{article_id}/translate", json={"start": start, "end": end}
        )
        second = client.post(
            f"/api/v1/articles/{article_id}/translate", json={"start": start, "end": end}
        )

        assert first.status_code == second.status_code == 200
        assert first.json()["selection_translation"] == second.json()["selection_translation"]
        assert len(fake_translation_provider.calls) == 1
        assert db_session.query(TranslationCache).count() == 1

    def test_cached_request_succeeds_even_if_provider_later_unconfigured(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client)
        start, end = _token_span(client, article_id, "Hund")
        client.post(f"/api/v1/articles/{article_id}/translate", json={"start": start, "end": end})

        app.dependency_overrides[deps.get_translation_provider] = lambda: NullTranslationProvider()
        response = client.post(
            f"/api/v1/articles/{article_id}/translate", json={"start": start, "end": end}
        )

        assert response.status_code == 200

    def test_rate_limit_counts_only_non_cached_requests(
        self, client: TestClient, db_session: Session, monkeypatch
    ) -> None:
        monkeypatch.setattr(get_settings(), "translation_rate_limit_per_hour", 1)
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client)
        hund_span = _token_span(client, article_id, "Hund")
        ich_span = _token_span(client, article_id, "Ich")

        first = client.post(
            f"/api/v1/articles/{article_id}/translate",
            json={"start": hund_span[0], "end": hund_span[1]},
        )
        assert first.status_code == 200

        rate_limited = client.post(
            f"/api/v1/articles/{article_id}/translate",
            json={"start": ich_span[0], "end": ich_span[1]},
        )
        assert rate_limited.status_code == 429
        assert rate_limited.json()["detail"]["code"] == "translation_rate_limited"
        assert "retry_after" in rate_limited.json()["detail"]

        cached_repeat = client.post(
            f"/api/v1/articles/{article_id}/translate",
            json={"start": hund_span[0], "end": hund_span[1]},
        )
        assert cached_repeat.status_code == 200
        assert db_session.query(TranslationRequestLog).count() == 1

    def test_offset_not_aligned_to_token_boundary_is_422(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client)
        start, end = _token_span(client, article_id, "Hund")

        response = client.post(
            f"/api/v1/articles/{article_id}/translate",
            json={"start": start + 1, "end": end},
        )

        assert response.status_code == 422

    def test_selection_crossing_sentence_boundary_is_422(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client)
        ich_start, _ = _token_span(client, article_id, "Ich")
        _, schlaeft_end = _token_span(client, article_id, "schläft")

        response = client.post(
            f"/api/v1/articles/{article_id}/translate",
            json={"start": ich_start, "end": schlaeft_end},
        )

        assert response.status_code == 422

    def test_other_user_gets_404(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client)
        client.post("/api/v1/auth/logout")

        _login_as(client, db_session, username="bailey_jones", email="bailey@example.com")
        response = client.post(
            f"/api/v1/articles/{article_id}/translate", json={"start": 0, "end": 3}
        )

        assert response.status_code == 404

    def test_unverified_user_gets_403(self, client: TestClient, db_session: Session) -> None:
        make_user(
            db_session, email="alex@example.com", username="alex_morgan", password=VALID_PASSWORD
        )
        client.post(
            "/api/v1/auth/login",
            json={"identifier": "alex_morgan", "password": VALID_PASSWORD},
        )

        response = client.post(
            "/api/v1/articles/00000000-0000-0000-0000-000000000000/translate",
            json={"start": 0, "end": 3},
        )

        assert response.status_code == 403

    def test_stored_cache_row_fields(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session, username="alex_morgan", email="alex@example.com")
        article_id = _create_article(client)
        start, end = _token_span(client, article_id, "Hund")

        client.post(f"/api/v1/articles/{article_id}/translate", json={"start": start, "end": end})

        row = db_session.query(TranslationCache).one()
        assert row.source_text == "Hund"
        assert row.target_lang == "EN-US"
        assert row.provider == "deepl"
        assert row.context is not None and "Hund" in row.context
