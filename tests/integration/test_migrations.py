"""Migration round-trip + model/migration drift check + DB-level guarantees.

Runs only when TEST_DATABASE_URL points at a disposable PostgreSQL database (CI provides one;
locally: `docker compose up -d db` and use a separate database name). The database is wiped.
"""

import asyncio
import os
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import Settings

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"

pytestmark = [
    pytest.mark.db,
    pytest.mark.skipif(not TEST_DATABASE_URL, reason="set TEST_DATABASE_URL to run DB tests"),
]


@pytest.fixture(scope="module")
def database_url() -> str:
    assert TEST_DATABASE_URL
    settings = Settings(_env_file=None, database_url=TEST_DATABASE_URL)  # type: ignore[call-arg]
    return settings.database_url


@pytest.fixture(scope="module")
def alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def test_upgrade_downgrade_roundtrip_matches_models(alembic_config: Config) -> None:
    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")
    command.check(alembic_config)  # fails if ORM models drifted from the migrations
    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")


def test_session_delete_cascades_and_enums_are_enforced(
    alembic_config: Config, database_url: str
) -> None:
    command.upgrade(alembic_config, "head")

    async def scenario() -> None:
        engine = create_async_engine(database_url)
        user_id, session_id = uuid.uuid4(), uuid.uuid4()
        try:
            async with engine.begin() as conn:
                await conn.execute(text("INSERT INTO users (id) VALUES (:id)"), {"id": user_id})
                await conn.execute(
                    text(
                        "INSERT INTO interview_sessions (id, user_id, status, role, level, mode,"
                        " current_turn) VALUES (:id, :user, 'ready', 'ai_engineer', 'fresher',"
                        " 'demo', 0)"
                    ),
                    {"id": session_id, "user": user_id},
                )
                await conn.execute(
                    text(
                        "INSERT INTO interview_turns (id, session_id, turn_no, question_id, kind,"
                        " skill_id, skill_version, question_text) VALUES (:id, :sid, 1, 'q_001',"
                        " 'main', 'rag_systems', '1.0.0', 'RAG là gì?')"
                    ),
                    {"id": uuid.uuid4(), "sid": session_id},
                )
                await conn.execute(
                    text("DELETE FROM interview_sessions WHERE id = :id"), {"id": session_id}
                )
                remaining = await conn.scalar(
                    text("SELECT count(*) FROM interview_turns WHERE session_id = :id"),
                    {"id": session_id},
                )
                assert remaining == 0

            with pytest.raises(IntegrityError):
                async with engine.begin() as conn:
                    await conn.execute(
                        text(
                            "INSERT INTO interview_sessions (id, user_id, status, role, level,"
                            " mode, current_turn) VALUES (:id, :user, 'ready', 'frontend',"
                            " 'fresher', 'demo', 0)"
                        ),
                        {"id": uuid.uuid4(), "user": user_id},
                    )
        finally:
            async with engine.begin() as conn:
                await conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
            await engine.dispose()

    asyncio.run(scenario())
