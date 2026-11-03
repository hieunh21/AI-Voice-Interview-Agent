"""Liveness (process is up) and readiness (dependencies reachable) probes."""

import asyncio
import logging
from typing import Literal

from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from app import __version__
from app.api.deps import DatabaseDep, SettingsDep

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["health"])

READINESS_TIMEOUT_SECONDS = 3.0


class HealthResponse(BaseModel):
    status: Literal["ok"]
    version: str
    environment: str


class ReadinessResponse(BaseModel):
    status: Literal["ready", "unavailable"]
    database: Literal["ok", "unreachable"]


@router.get("", response_model=HealthResponse)
async def liveness(settings: SettingsDep) -> HealthResponse:
    return HealthResponse(status="ok", version=__version__, environment=settings.app_env)


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse}},
)
async def readiness(db: DatabaseDep, response: Response) -> ReadinessResponse:
    try:
        await asyncio.wait_for(db.ping(), timeout=READINESS_TIMEOUT_SECONDS)
    except Exception as exc:  # any failure means "not ready"; details stay in server logs
        logger.warning("Readiness check failed: database unreachable (%s)", type(exc).__name__)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(status="unavailable", database="unreachable")
    return ReadinessResponse(status="ready", database="ok")
