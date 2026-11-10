from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def _app_connect_args() -> dict[str, str]:
    settings = get_settings()
    return {
        "options": (
            f"-c statement_timeout={settings.db_statement_timeout_ms} "
            f"-c lock_timeout={settings.db_lock_timeout_ms}"
        )
    }


# Bounded by statement_timeout/lock_timeout (see Settings) — a query stuck behind a lock
# fails fast instead of hanging a request forever; app/main.py maps the resulting
# OperationalError to a clean 503/504 instead of a 500 with a stack trace. Alembic
# (migrations/env.py) and the dictionary import script (app/scripts/import_dictionary.py)
# build their own separate, untimed engines — never reuse this one for either, since both
# legitimately run longer than these timeouts allow.
engine = create_engine(
    get_settings().database_url, pool_pre_ping=True, connect_args=_app_connect_args()
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# A second, separate engine with no statement_timeout/lock_timeout, for the handful of
# scripts that legitimately run longer than the app's own bound (the dictionary import in
# particular can take minutes). Alembic already builds its own independent engine
# (migrations/env.py) and never touches either of these.
untimed_engine = create_engine(get_settings().database_url, pool_pre_ping=True)
UntimedSessionLocal = sessionmaker(bind=untimed_engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
