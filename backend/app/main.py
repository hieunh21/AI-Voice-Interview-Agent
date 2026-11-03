"""Application factory. Run with: `uvicorn app.main:create_app --factory --reload`."""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ai.evaluation.evaluator import Evaluator
from ai.graphs.interview_graph import Interviewer
from ai.llm.base import StructuredLLM
from app import __version__
from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.runtime import (
    build_llm,
    build_preparer,
    build_stt,
    build_tts,
    load_validated_library,
)
from app.db import Database
from app.services.interviews import ServiceError
from app.services.reports import ReportJobs
from speech.interfaces import SpeechToText, TextToSpeech

logger = logging.getLogger("app")
SHUTDOWN_GRACE_SECONDS = 20

_BUILD_FROM_SETTINGS: Any = object()


def create_app(
    settings: Settings | None = None,
    *,
    llm: StructuredLLM | None = _BUILD_FROM_SETTINGS,
    stt: SpeechToText | None = _BUILD_FROM_SETTINGS,
    tts: TextToSpeech | None = _BUILD_FROM_SETTINGS,
) -> FastAPI:
    """Build the app. Tests may inject fakes (or None) for the LLM and speech providers."""
    settings = settings or get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    library = load_validated_library(settings)
    if llm is _BUILD_FROM_SETTINGS:
        llm = build_llm(settings)
    if stt is _BUILD_FROM_SETTINGS:
        stt = build_stt(settings)
    if tts is _BUILD_FROM_SETTINGS:
        tts = build_tts(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        logger.info(
            "IntervAI API %s starting (env=%s, draft_playbooks=%s, llm=%s, stt=%s, tts=%s)",
            __version__,
            settings.app_env,
            settings.allow_draft_playbooks,
            llm.model_id if llm else "none",
            stt.provider_id if stt else "none",
            tts.provider_id if tts else "browser",
        )
        try:
            resumed = await app.state.reports.resume_pending()
            if resumed:
                logger.info("Re-queued %d unfinished report job(s)", resumed)
        except Exception as exc:  # the API must start even if the database is not reachable yet
            logger.warning("Could not resume report jobs: %s", type(exc).__name__)
        yield
        try:
            await asyncio.wait_for(app.state.reports.wait_idle(), timeout=SHUTDOWN_GRACE_SECONDS)
        except TimeoutError:
            logger.warning("Shutting down with report jobs running; they resume on next start")
        closer = getattr(app.state.tts, "aclose", None)
        if closer is not None:
            await closer()
        await app.state.db.dispose()

    app = FastAPI(
        title="IntervAI API",
        version=__version__,
        lifespan=lifespan,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
    )
    app.state.settings = settings
    app.state.db = Database(settings.database_url)
    app.state.library = library
    app.state.preparer = build_preparer(settings, library, llm)
    app.state.interviewer = Interviewer(llm)
    app.state.stt = stt
    app.state.tts = tts
    app.state.reports = ReportJobs(app.state.db, Evaluator(llm))

    @app.exception_handler(ServiceError)
    async def _service_error(_: Request, exc: ServiceError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type", "Authorization", "Idempotency-Key"],
    )
    app.include_router(api_router, prefix="/api")
    return app
