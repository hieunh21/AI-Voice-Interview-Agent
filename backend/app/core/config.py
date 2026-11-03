"""Typed, validated settings. The app refuses to start when the environment is invalid."""

from functools import lru_cache
from typing import Annotated, Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_ASYNC_SCHEME = "postgresql+asyncpg://"
_PLAIN_SCHEMES = ("postgres://", "postgresql://")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    database_url: str
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]
    allow_draft_playbooks: bool = False
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-3.8-flash"
    # Optional Gemini-compatible gateway; empty means Google's endpoint.
    gemini_base_url: str | None = None
    llm_timeout_seconds: float = Field(default=45, gt=0, le=300)
    planner_context_chars: int = Field(default=24_000, ge=2_000, le=100_000)
    max_upload_bytes: int = Field(default=5 * 1024 * 1024, ge=1024, le=20 * 1024 * 1024)

    # Voice. STT reuses the Gemini key/gateway; TTS needs ElevenLabs key + voice.
    elevenlabs_api_key: SecretStr | None = None
    elevenlabs_model: str = "eleven_flash_v2_5"
    elevenlabs_voice_id: str | None = None
    tts_timeout_seconds: float = Field(default=20, gt=0, le=120)
    stt_timeout_seconds: float = Field(default=45, gt=0, le=180)
    max_audio_bytes: int = Field(default=8 * 1024 * 1024, ge=10_000, le=25 * 1024 * 1024)

    @field_validator("database_url")
    @classmethod
    def _normalise_database_url(cls, value: str) -> str:
        """Accept the plain URLs that managed Postgres providers hand out."""
        value = value.strip()
        for scheme in _PLAIN_SCHEMES:
            if value.startswith(scheme):
                return _ASYNC_SCHEME + value.removeprefix(scheme)
        if not value.startswith(_ASYNC_SCHEME):
            raise ValueError("DATABASE_URL must be a PostgreSQL URL (postgresql+asyncpg://...)")
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip().rstrip("/") for origin in value.split(",") if origin.strip()]
        return value

    @field_validator(
        "gemini_api_key",
        "gemini_base_url",
        "elevenlabs_api_key",
        "elevenlabs_voice_id",
        mode="before",
    )
    @classmethod
    def _empty_is_none(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("gemini_base_url")
    @classmethod
    def _https_base_url(cls, value: str | None) -> str | None:
        if value is not None and not value.startswith("https://"):
            raise ValueError("GEMINI_BASE_URL must be an https:// URL")
        return value.rstrip("/") if value else value

    @model_validator(mode="after")
    def _production_rules(self) -> Self:
        if self.app_env != "production":
            return self
        problems: list[str] = []
        if self.allow_draft_playbooks:
            problems.append("ALLOW_DRAFT_PLAYBOOKS must be false in production")
        if not self.cors_origins or "*" in self.cors_origins:
            problems.append("CORS_ORIGINS must list explicit origins in production")
        insecure = [o for o in self.cors_origins if not o.startswith("https://")]
        if insecure:
            problems.append(f"CORS_ORIGINS must use https in production: {insecure}")
        if problems:
            raise ValueError("; ".join(problems))
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # values come from the environment
