import logging
import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import BACKEND_DIR, ENV_FILE, Settings, configured_integrations
from app.main import app


def test_env_file_is_absolute_and_inside_backend() -> None:
    assert ENV_FILE.is_absolute()
    assert ENV_FILE == BACKEND_DIR / ".env"
    assert (BACKEND_DIR / "app" / "core" / "config.py").is_file()


def test_absolute_env_file_loads_regardless_of_working_directory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # tempfile rather than pytest's tmp_path, which some Windows setups can't create.
    with tempfile.TemporaryDirectory() as directory:
        env_file = Path(directory) / "backend.env"
        env_file.write_text("GENIUS_ACCESS_TOKEN=from-env-file-not-real\n", encoding="utf-8")
        monkeypatch.delenv("GENIUS_ACCESS_TOKEN", raising=False)
        # Start "the server" from an unrelated directory: an absolute path must still load.
        monkeypatch.chdir(os.path.abspath(os.sep))

        settings = Settings(_env_file=env_file)

    assert settings.genius_access_token == "from-env-file-not-real"


def test_missing_env_file_falls_back_to_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GENIUS_ACCESS_TOKEN", raising=False)

    settings = Settings(_env_file=BACKEND_DIR / "does-not-exist-for-tests.env")

    assert settings.genius_access_token == ""


def test_configured_integrations_reports_booleans_only() -> None:
    secret = "secret-value-not-real"
    settings = Settings(
        _env_file=None,
        genius_access_token=secret,
        deepl_api_key="",
        smtp_host="localhost",
        smtp_username="",
        smtp_password=secret,
    )

    summary = configured_integrations(settings)

    assert summary["genius"] is True
    assert summary["deepl"] is False
    assert summary["smtp"] is True
    assert summary["smtp_auth"] is False
    assert all(isinstance(value, bool) for value in summary.values())
    assert secret not in repr(summary)


def test_startup_logs_integrations_without_values(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = "secret-value-not-real"
    monkeypatch.setattr(
        "app.main.get_settings",
        lambda: Settings(_env_file=None, genius_access_token=secret, deepl_api_key=secret),
    )

    # The session's Alembic run (fileConfig) disables already-created loggers; the real
    # server never does that, so re-enable it for this assertion only.
    monkeypatch.setattr(logging.getLogger("uvicorn.error"), "disabled", False)

    with caplog.at_level(logging.INFO, logger="uvicorn.error"), TestClient(app):
        pass

    lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith("integrations:")]
    assert len(lines) == 1
    assert "genius: configured" in lines[0]
    assert "deepl: configured" in lines[0]
    assert secret not in caplog.text
