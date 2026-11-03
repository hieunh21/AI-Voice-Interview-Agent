import uuid

from fastapi import APIRouter, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from ai.schemas.enums import DocumentKind
from ai.schemas.interview import InterviewSetup
from app.api.deps import CurrentUser, InterviewerDep, PreparerDep, SessionDep, SettingsDep
from app.core.config import Settings
from app.models import User
from app.schemas.interview import AnswerRequest, SessionSummary, SessionView
from app.services import interviews as service
from app.services import live
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
) -> SessionView:
    """Record the answer to the pending turn, then ask a follow-up, the next question, or finish.

    Retrying with the same `request_id` is a no-op; a stale `turn_no` is rejected with 409.
    """
    session = await service.get_owned_session(db, user, session_id)
    await live.submit_answer(
        db,
        session,
        interviewer,
        request_id=body.request_id,
        turn_no=body.turn_no,
        answer_text=body.answer_text,
    )
    return await service.session_view(db, session)


@router.post("/{session_id}/finish", response_model=SessionView)
async def finish_interview(session_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> SessionView:
    """End the interview early (answered turns are kept). Idempotent."""
    session = await service.get_owned_session(db, user, session_id)
    await live.finish_interview(db, session)
    return await service.session_view(db, session)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_interview(session_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> Response:
    """Delete the session with its documents, plan, transcript and report."""
    session = await service.get_owned_session(db, user, session_id)
    await service.delete_session(db, session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
