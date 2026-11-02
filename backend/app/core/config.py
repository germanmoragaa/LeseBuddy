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


@lru_cache
def get_settings() -> Settings:
    return Settings()
