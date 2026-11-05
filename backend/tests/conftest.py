from collections.abc import Generator

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.api.deps import get_email_sender, get_translation_provider
from app.core.config import get_settings
from app.core.db import get_db
from app.main import app
from app.services.email import FakeEmailSender
from app.services.translation.fake_provider import FakeTranslationProvider


@pytest.fixture(scope="session", autouse=True)
def apply_migrations() -> None:
    settings = get_settings()
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", settings.test_database_url)
    command.upgrade(alembic_cfg, "head")


@pytest.fixture(scope="session")
def test_engine() -> Generator[Engine, None, None]:
    engine = create_engine(get_settings().test_database_url)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine: Engine) -> Generator[Session, None, None]:
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def fake_email_sender() -> FakeEmailSender:
    return FakeEmailSender()


@pytest.fixture
def fake_translation_provider() -> FakeTranslationProvider:
    return FakeTranslationProvider()


@pytest.fixture
def client(
    db_session: Session,
    fake_email_sender: FakeEmailSender,
    fake_translation_provider: FakeTranslationProvider,
) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    def override_get_email_sender() -> FakeEmailSender:
        return fake_email_sender

    def override_get_translation_provider() -> FakeTranslationProvider:
        return fake_translation_provider

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_email_sender] = override_get_email_sender
    app.dependency_overrides[get_translation_provider] = override_get_translation_provider
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
