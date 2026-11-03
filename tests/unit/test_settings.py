from typing import Any

import pytest
from pydantic import ValidationError

from app.core.config import Settings

DB = "postgresql+asyncpg://u:p@localhost:5432/db"


def _settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "app_env": "development",
        "database_url": DB,
        "cors_origins": "http://localhost:5173",
        "allow_draft_playbooks": False,
        "gemini_api_key": "",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)  # type: ignore[call-arg]


@pytest.mark.parametrize("scheme", ["postgres://", "postgresql://"])
def test_plain_postgres_urls_are_normalised_to_asyncpg(scheme: str) -> None:
    settings = _settings(database_url=f"{scheme}u:p@db.example.com:5432/app")
    assert settings.database_url == "postgresql+asyncpg://u:p@db.example.com:5432/app"


def test_non_postgres_url_is_rejected() -> None:
    with pytest.raises(ValidationError, match="PostgreSQL"):
        _settings(database_url="sqlite:///local.db")


def test_cors_origins_are_split_and_trimmed() -> None:
    settings = _settings(cors_origins=" http://localhost:5173/ , https://intervai.app ")
    assert settings.cors_origins == ["http://localhost:5173", "https://intervai.app"]


def test_empty_api_key_is_none() -> None:
    assert _settings().gemini_api_key is None


def test_gemini_base_url_is_optional_and_must_be_https() -> None:
    assert _settings(gemini_base_url="").gemini_base_url is None
    assert _settings(gemini_base_url="https://gw.example/").gemini_base_url == "https://gw.example"
    with pytest.raises(ValidationError, match="https"):
        _settings(gemini_base_url="http://gw.example")


def test_valid_production_settings() -> None:
    settings = _settings(app_env="production", cors_origins="https://intervai.app")
    assert settings.is_production


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"allow_draft_playbooks": True}, "ALLOW_DRAFT_PLAYBOOKS"),
        ({"cors_origins": "*"}, "explicit origins"),
        ({"cors_origins": "http://intervai.app"}, "https"),
    ],
)
def test_production_rules(overrides: dict[str, Any], message: str) -> None:
    values = {"app_env": "production", "cors_origins": "https://intervai.app", **overrides}
    with pytest.raises(ValidationError, match=message):
        _settings(**values)
