"""Shared fixtures for tests that need PostgreSQL (TEST_DATABASE_URL, a disposable database)."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from helpers import MAX_UPLOAD, TEST_DATABASE_URL, fake_llm, run_sql

from app.core.config import Settings
from app.main import create_app

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"


@pytest.fixture(scope="session")
def settings() -> Settings:
    assert TEST_DATABASE_URL
    return Settings(  # type: ignore[call-arg]
        _env_file=None,
        app_env="test",
        database_url=TEST_DATABASE_URL,
        cors_origins="http://localhost:5173",
        allow_draft_playbooks=True,
        max_upload_bytes=MAX_UPLOAD,
    )


@pytest.fixture(scope="session")
def migrated(settings: Settings) -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
    command.upgrade(config, "head")


@pytest.fixture
def client(settings: Settings, migrated: None) -> Iterator[TestClient]:
    run_sql(settings.database_url, "TRUNCATE users CASCADE")
    with TestClient(create_app(settings, llm=fake_llm())) as test_client:
        yield test_client
