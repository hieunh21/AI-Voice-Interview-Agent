"""FastAPI dependencies resolved from application state (set up in `create_app`)."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ai.graphs.interview_graph import Interviewer
from ai.graphs.prep_graph import Preparer
from ai.playbook_loader import PlaybookLibrary
from app.core.config import Settings
from app.db import Database
from app.models import User
from app.services.auth import user_for_token
from app.services.reports import ReportJobs
from speech.interfaces import SpeechToText, TextToSpeech

_bearer = HTTPBearer(auto_error=False)


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_database(request: Request) -> Database:
    return request.app.state.db


def get_preparer(request: Request) -> Preparer:
    return request.app.state.preparer


def get_interviewer(request: Request) -> Interviewer:
    return request.app.state.interviewer


def get_reports(request: Request) -> ReportJobs:
    return request.app.state.reports


def get_library(request: Request) -> PlaybookLibrary:
    return request.app.state.library


def get_stt(request: Request) -> SpeechToText | None:
    return request.app.state.stt


def get_tts(request: Request) -> TextToSpeech | None:
    return request.app.state.tts


async def get_session(
    db: Annotated[Database, Depends(get_database)],
) -> AsyncIterator[AsyncSession]:
    async for session in db.session():
        yield session


SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
DatabaseDep = Annotated[Database, Depends(get_database)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]
PreparerDep = Annotated[Preparer, Depends(get_preparer)]
InterviewerDep = Annotated[Interviewer, Depends(get_interviewer)]
LibraryDep = Annotated[PlaybookLibrary, Depends(get_library)]
ReportsDep = Annotated[ReportJobs, Depends(get_reports)]
SpeechToTextDep = Annotated[SpeechToText | None, Depends(get_stt)]
TextToSpeechDep = Annotated[TextToSpeech | None, Depends(get_tts)]


async def get_current_user(
    db: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    user = await user_for_token(db, credentials.credentials) if credentials else None
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
