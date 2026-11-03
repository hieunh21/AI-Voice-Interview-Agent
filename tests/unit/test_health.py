from fastapi.testclient import TestClient

from app import __version__
from app.core.config import Settings
from app.main import create_app


def _client(database_url: str) -> TestClient:
    settings = Settings(  # type: ignore[call-arg]
        _env_file=None,
        app_env="test",
        database_url=database_url,
        cors_origins="http://localhost:5173",
        allow_draft_playbooks=True,
    )
    return TestClient(create_app(settings, llm=None))


def test_liveness_reports_version_and_environment() -> None:
    with _client("postgresql+asyncpg://u:p@localhost:5432/db") as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__, "environment": "test"}


def test_readiness_is_503_when_database_is_unreachable() -> None:
    with _client("postgresql+asyncpg://u:p@127.0.0.1:1/db") as client:
        response = client.get("/api/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "unreachable"}


def test_cors_allows_configured_origin_only() -> None:
    with _client("postgresql+asyncpg://u:p@localhost:5432/db") as client:
        allowed = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
        denied = client.get("/api/health", headers={"Origin": "https://evil.example"})
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in denied.headers
