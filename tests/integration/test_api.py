"""API flow against a real PostgreSQL (TEST_DATABASE_URL) with a fake LLM."""

import asyncio
import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from helpers import CV_TEXT, JD_TEXT, fake_llm, make_pdf
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from ai.schemas.interview import InterviewPlan
from app.core.config import Settings
from app.main import create_app

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
MAX_UPLOAD = 50_000

pytestmark = [
    pytest.mark.db,
    pytest.mark.skipif(not TEST_DATABASE_URL, reason="set TEST_DATABASE_URL to run DB tests"),
]


@pytest.fixture(scope="module")
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


@pytest.fixture(scope="module")
def migrated(settings: Settings) -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
    command.upgrade(config, "head")


def _sql(settings: Settings, statement: str, **params):
    async def run():
        engine = create_async_engine(settings.database_url)
        try:
            async with engine.begin() as conn:
                result = await conn.execute(text(statement), params)
                return result.all() if result.returns_rows else None
        finally:
            await engine.dispose()

    return asyncio.run(run())


@pytest.fixture
def client(settings: Settings, migrated: None) -> Iterator[TestClient]:
    _sql(settings, "TRUNCATE users CASCADE")
    with TestClient(create_app(settings, llm=fake_llm())) as test_client:
        yield test_client


def _guest(client: TestClient) -> dict[str, str]:
    response = client.post("/api/auth/guest")
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['token']}"}


def _create(client: TestClient, headers: dict[str, str], **payload) -> dict:
    body = {"role": "ai_engineer", "level": "fresher", "mode": "demo", **payload}
    response = client.post("/api/interviews", json=body, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_endpoints_require_a_guest_token(client: TestClient) -> None:
    assert client.get("/api/interviews").status_code == 401
    bad = {"Authorization": "Bearer not-a-real-token"}
    assert client.get("/api/interviews", headers=bad).status_code == 401


def test_role_and_level_only_flow(client: TestClient, settings: Settings) -> None:
    headers = _guest(client)
    session = _create(client, headers)
    assert session["status"] == "created"
    assert session["plan_preview"] is None
    assert (session["has_cv"], session["has_jd"]) == (False, False)

    prepared = client.post(f"/api/interviews/{session['id']}/prepare", headers=headers)
    assert prepared.status_code == 200, prepared.text
    view = prepared.json()
    assert view["status"] == "ready"
    preview = view["plan_preview"]
    assert preview["main_questions"] == 3
    assert sum(s["target_questions"] for s in preview["skills"]) == 3
    assert preview["input_sources"] == ["role_config", "role_playbook", "competency_skills"]
    assert "expected_points" not in prepared.text  # the client never sees the answers

    again = client.post(f"/api/interviews/{session['id']}/prepare", headers=headers)
    assert again.json()["plan_preview"] == preview  # idempotent

    [(plan_json,)] = _sql(
        settings,
        "SELECT plan_json FROM interview_plans WHERE session_id = :id",
        id=uuid.UUID(session["id"]),
    )
    plan = InterviewPlan.model_validate(plan_json)
    assert plan.versions.planner_model == "fake-llm"
    assert all(q.expected_points and q.rubric for q in plan.questions)
    assert plan.rubric_criteria["technical_accuracy"].anchors[5]

    listed = client.get("/api/interviews", headers=headers).json()
    assert [s["id"] for s in listed] == [session["id"]]

    assert client.delete(f"/api/interviews/{session['id']}", headers=headers).status_code == 204
    assert client.get(f"/api/interviews/{session['id']}", headers=headers).status_code == 404
    assert _sql(settings, "SELECT count(*) FROM interview_plans")[0][0] == 0


def test_documents_personalise_the_plan(client: TestClient) -> None:
    headers = _guest(client)
    session = _create(client, headers, jd_text=JD_TEXT)
    uploaded = client.post(
        f"/api/interviews/{session['id']}/cv",
        headers=headers,
        files={"file": ("cv.txt", CV_TEXT.encode(), "text/plain")},
    )
    assert uploaded.status_code == 200, uploaded.text
    assert (uploaded.json()["has_cv"], uploaded.json()["has_jd"]) == (True, True)

    view = client.post(f"/api/interviews/{session['id']}/prepare", headers=headers).json()
    assert view["plan_preview"]["input_sources"][-2:] == ["cv", "jd"]
    assert any("Kubernetes" in w for w in view["plan_preview"]["warnings"])


def test_new_document_invalidates_an_existing_plan(client: TestClient) -> None:
    headers = _guest(client)
    session = _create(client, headers)
    client.post(f"/api/interviews/{session['id']}/prepare", headers=headers)
    pdf = make_pdf("Backend developer with FastAPI and PostgreSQL experience in production")
    view = client.post(
        f"/api/interviews/{session['id']}/cv",
        headers=headers,
        files={"file": ("cv.pdf", pdf, "application/pdf")},
    ).json()
    assert view["status"] == "created"
    assert view["plan_preview"] is None


@pytest.mark.parametrize(
    ("filename", "data", "status"),
    [
        ("photo.jpg", b"\xff\xd8\xff\xe0", 422),
        ("scan.pdf", make_pdf(""), 422),
        ("big.txt", b"a" * (MAX_UPLOAD + 1), 413),
    ],
)
def test_bad_uploads_are_rejected(client: TestClient, filename, data, status) -> None:
    headers = _guest(client)
    session = _create(client, headers)
    response = client.post(
        f"/api/interviews/{session['id']}/cv", headers=headers, files={"file": (filename, data)}
    )
    assert response.status_code == status
    assert response.json()["detail"]


def test_sessions_are_private_to_their_owner(client: TestClient) -> None:
    owner, stranger = _guest(client), _guest(client)
    session = _create(client, owner)
    for method, path in [
        ("get", f"/api/interviews/{session['id']}"),
        ("post", f"/api/interviews/{session['id']}/prepare"),
        ("delete", f"/api/interviews/{session['id']}"),
    ]:
        assert getattr(client, method)(path, headers=stranger).status_code == 404
    assert client.get("/api/interviews", headers=stranger).json() == []


def test_invalid_setup_is_rejected(client: TestClient) -> None:
    headers = _guest(client)
    for payload in ({"level": "fresher"}, {"role": "frontend", "level": "fresher"}):
        assert client.post("/api/interviews", json=payload, headers=headers).status_code == 422
