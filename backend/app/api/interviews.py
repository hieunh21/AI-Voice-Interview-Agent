import uuid

from fastapi import APIRouter, Response, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ai.schemas.enums import DocumentKind
from ai.schemas.interview import InterviewSetup
from app.api.deps import (
    CurrentUser,
    InterviewerDep,
    LibraryDep,
    PreparerDep,
    ReportsDep,
    SessionDep,
    SettingsDep,
    SpeechToTextDep,
    TextToSpeechDep,
)
from app.core.config import Settings
from app.models import User
from app.schemas.interview import AnswerRequest, ReportResponse, SessionSummary, SessionView
from app.services import interviews as service
from app.services import live, voice
from app.services import reports as reports_service
from app.services.interviews import ServiceError

router = APIRouter(prefix="/interviews", tags=["interviews"])


@router.post("", response_model=SessionView, status_code=status.HTTP_201_CREATED)
async def create_interview(setup: InterviewSetup, user: CurrentUser, db: SessionDep) -> SessionView:
    """Create a session from role + level (required) and optional pasted CV/JD text."""
    session = await service.create_session(db, user, setup)
    return await service.session_view(db, session)


@router.get("", response_model=list[SessionSummary])
async def list_interviews(user: CurrentUser, db: SessionDep) -> list[SessionSummary]:
    return await service.list_sessions(db, user)


@router.get("/{session_id}", response_model=SessionView)
async def get_interview(session_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> SessionView:
    session = await service.get_owned_session(db, user, session_id)
    return await service.session_view(db, session)


async def _upload(
    kind: DocumentKind,
    session_id: uuid.UUID,
    file: UploadFile,
    user: User,
    db: AsyncSession,
    settings: Settings,
) -> SessionView:
    session = await service.get_owned_session(db, user, session_id)
    data = await file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        limit_mb = settings.max_upload_bytes // (1024 * 1024)
        raise ServiceError(413, f"File quá lớn (tối đa {limit_mb} MB).")
    await service.attach_document(
        db,
        session,
        kind,
        data=data,
        filename=file.filename or "",
        content_type=file.content_type,
    )
    return await service.session_view(db, session)


@router.post("/{session_id}/cv", response_model=SessionView)
async def upload_cv(
    session_id: uuid.UUID,
    file: UploadFile,
    user: CurrentUser,
    db: SessionDep,
    settings: SettingsDep,
) -> SessionView:
    """Attach or replace the optional CV (PDF with a text layer, or TXT)."""
    return await _upload(DocumentKind.CV, session_id, file, user, db, settings)


@router.post("/{session_id}/jd", response_model=SessionView)
async def upload_jd(
    session_id: uuid.UUID,
    file: UploadFile,
    user: CurrentUser,
    db: SessionDep,
    settings: SettingsDep,
) -> SessionView:
    """Attach or replace the optional job description (PDF or TXT)."""
    return await _upload(DocumentKind.JD, session_id, file, user, db, settings)


@router.post("/{session_id}/prepare", response_model=SessionView)
async def prepare_interview(
    session_id: uuid.UUID, user: CurrentUser, db: SessionDep, preparer: PreparerDep
) -> SessionView:
    """Build and freeze the InterviewPlan. Idempotent once the session is ready."""
    session = await service.get_owned_session(db, user, session_id)
    await service.prepare_session(db, session, preparer)
    return await service.session_view(db, session)


@router.post("/{session_id}/start", response_model=SessionView)
async def start_interview(session_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> SessionView:
    """Start a prepared session and ask the first planned question. Idempotent."""
    session = await service.get_owned_session(db, user, session_id)
    await live.start_interview(db, session)
    return await service.session_view(db, session)


@router.post("/{session_id}/answer", response_model=SessionView)
async def answer_question(
    session_id: uuid.UUID,
    body: AnswerRequest,
    user: CurrentUser,
    db: SessionDep,
    interviewer: InterviewerDep,
    reports: ReportsDep,
) -> SessionView:
    """Record the answer to the pending turn, then ask a follow-up, the next question, or finish.

    Retrying with the same `request_id` is a no-op; a stale `turn_no` is rejected with 409.
    When the interview ends, the evaluation report is scheduled in the background.
    """
    session = await service.get_owned_session(db, user, session_id)
    completed = await live.submit_answer(
        db,
        session,
        interviewer,
        request_id=body.request_id,
        turn_no=body.turn_no,
        answer_text=body.answer_text,
        answer_mode=body.answer_mode,
    )
    if completed:
        reports.schedule(session.id)
    return await service.session_view(db, session)


class TranscriptResponse(BaseModel):
    text: str
    latency_ms: int


@router.post("/{session_id}/transcribe", response_model=TranscriptResponse)
async def transcribe_answer(
    session_id: uuid.UUID,
    file: UploadFile,
    user: CurrentUser,
    db: SessionDep,
    stt: SpeechToTextDep,
    library: LibraryDep,
    settings: SettingsDep,
) -> TranscriptResponse:
    """Recorded answer → editable transcript. The audio is discarded after recognition."""
    session = await service.get_owned_session(db, user, session_id)
    data = await file.read(settings.max_audio_bytes + 1)
    text, latency_ms = await voice.transcribe_answer(
        db,
        session,
        stt,
        library,
        data=data,
        content_type=file.content_type,
        max_bytes=settings.max_audio_bytes,
    )
    return TranscriptResponse(text=text, latency_ms=latency_ms)


@router.get("/{session_id}/turns/{turn_no}/audio")
async def question_audio(
    session_id: uuid.UUID, turn_no: int, user: CurrentUser, db: SessionDep, tts: TextToSpeechDep
) -> Response:
    """Spoken version of one of this session's questions (audio/mpeg)."""
    session = await service.get_owned_session(db, user, session_id)
    audio = await voice.question_audio(db, session, tts, turn_no)
    return Response(
        content=audio.data,
        media_type=audio.mime_type,
        headers={"Cache-Control": "private, max-age=86400"},
    )


@router.post("/{session_id}/finish", response_model=SessionView)
async def finish_interview(
    session_id: uuid.UUID, user: CurrentUser, db: SessionDep, reports: ReportsDep
) -> SessionView:
    """End the interview early (answered turns are kept, then evaluated). Idempotent."""
    session = await service.get_owned_session(db, user, session_id)
    if await live.finish_interview(db, session):
        reports.schedule(session.id)
    return await service.session_view(db, session)


@router.get("/{session_id}/report", response_model=ReportResponse)
async def get_report(session_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> ReportResponse:
    """Report status (pending/processing/completed/failed) and the report once completed."""
    session = await service.get_owned_session(db, user, session_id)
    status_, report = await reports_service.get_report(db, session.id)
    return ReportResponse(status=status_, report=report)


@router.post("/{session_id}/report/retry", response_model=ReportResponse)
async def retry_report(
    session_id: uuid.UUID, user: CurrentUser, db: SessionDep, reports: ReportsDep
) -> ReportResponse:
    """Re-run a failed evaluation (never creates a second report)."""
    session = await service.get_owned_session(db, user, session_id)
    if await reports_service.retry_report(db, session.id):
        reports.schedule(session.id)
    status_, report = await reports_service.get_report(db, session.id)
    return ReportResponse(status=status_, report=report)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_interview(session_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> Response:
    """Delete the session with its documents, plan, transcript and report."""
    session = await service.get_owned_session(db, user, session_id)
    await service.delete_session(db, session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
