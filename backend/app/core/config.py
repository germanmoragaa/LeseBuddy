from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ — resolved from this file, not the working directory, so `.env` loads the same way
# whether the server is started from backend/, the repo root, or an IDE launcher. A missing
# file (CI) is fine: pydantic-settings skips it and the defaults/real env vars apply.
BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://lesebuddy:lesebuddy@localhost:5432/lesebuddy"
    test_database_url: str = (
        "postgresql+psycopg://lesebuddy:lesebuddy@localhost:5432/lesebuddy_test"
    )

    # Applied only to the app's own request-scoped engine (app/core/db.py) — never to
    # Alembic or the dictionary import script, both of which legitimately run longer than
    # this. A query stuck behind a lock (e.g. an orphaned import transaction) fails fast with
    # a clean error instead of hanging a request forever.
    db_statement_timeout_ms: int = 5000
    db_lock_timeout_ms: int = 3000

    # False for local http development; set true wherever the app is served over https.
    session_cookie_secure: bool = False
    session_duration_days: int = 30

    # Used to key the HMAC that hashes email verification codes. MUST be overridden with a
    # real random value outside local development.
    secret_key: str = "dev-only-insecure-secret-change-in-production"

    # SMTP defaults point at the Mailpit service in docker-compose.yml (no auth, no TLS).
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = False
    email_from: str = "LeseBuddy <noreply@lesebuddy.local>"

    verification_code_ttl_minutes: int = 15
    verification_code_max_attempts: int = 5
    verification_resend_cooldown_seconds: int = 60
    verification_resend_hourly_cap: int = 5
    unverified_account_ttl_hours: int = 24

    # DeepL API (Free plan). Empty means "not configured" — the app still starts, translation
    # requests return a clear not-configured error instead of failing at startup.
    deepl_api_key: str = ""
    # DeepL target-language code used when a user has no stored preference yet.
    translation_default_language: str = "EN-US"
    # Per-user cap on non-cached (real, billed) translation requests. Cached hits never count.
    translation_rate_limit_per_hour: int = 60
    # How long a cached DeepL usage snapshot is trusted before re-checking — avoids doubling
    # DeepL round trips on every translation request just to monitor the monthly quota.
    translation_usage_check_interval_seconds: int = 300
    # Above this fraction of the monthly character quota, degrade with a warning.
    translation_usage_warn_threshold: float = 0.9

    # Genius API client access token — song search and metadata only, never lyrics (see
    # docs/decisions/0006-songs-and-lyrics.md). Empty means "not configured": the app still
    # starts, and song search will report that it's unavailable.
    genius_access_token: str = ""
    # Per-user cap on song searches per rolling minute (cached hits count too). In memory,
    # single-process only — see app/services/songs/rate_limit.py.
    songs_search_rate_limit_per_minute: int = 30
    # How long a song search/metadata result is reused before asking Genius again.
    songs_cache_ttl_seconds: int = 600


def configured_integrations(settings: Settings) -> dict[str, bool]:
    """Which optional integrations are configured — booleans only, so it's safe to log.
    Never add a value (token, key, password, host) to this."""
    return {
        "env_file": ENV_FILE.is_file(),
        "genius": bool(settings.genius_access_token),
        "deepl": bool(settings.deepl_api_key),
        "smtp": bool(settings.smtp_host),
        "smtp_auth": bool(settings.smtp_username and settings.smtp_password),
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
