from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://lesebuddy:lesebuddy@localhost:5432/lesebuddy"
    test_database_url: str = (
        "postgresql+psycopg://lesebuddy:lesebuddy@localhost:5432/lesebuddy_test"
    )

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
