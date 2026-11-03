"""Interview session use-cases: create, attach optional documents, prepare the plan, view, delete.

Business rules live here (not in the LLM): ownership, allowed status transitions, document limits,
and the atomic "claim" that prevents two concurrent prepare runs for one session.
"""

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ai.documents import DocumentError, extract_text
from ai.graphs.prep_graph import Preparer
from ai.playbook_selector import SelectionError
from ai.schemas.enums import DocumentKind, DocumentSource, SessionStatus
from ai.schemas.interview import MAX_CV_CHARS, MAX_JD_CHARS, InterviewPlan, InterviewSetup
from app.models import (
    InterviewPlanRecord,
    InterviewReportRecord,
    InterviewSession,
    InterviewTurn,
    SessionDocument,
    User,
)
from app.schemas.interview import PlanPreview, SessionSummary, SessionView, TurnView

logger = logging.getLogger(__name__)

MAX_DOCUMENT_CHARS = {DocumentKind.CV: MAX_CV_CHARS, DocumentKind.JD: MAX_JD_CHARS}
DOCUMENT_LABEL = {DocumentKind.CV: "CV", DocumentKind.JD: "JD"}
EDITABLE_STATUSES = (SessionStatus.CREATED, SessionStatus.READY, SessionStatus.FAILED)
CLAIMABLE_STATUSES = (SessionStatus.CREATED, SessionStatus.FAILED)
LIST_LIMIT = 50


@dataclass
class ServiceError(Exception):
    """A user-facing failure mapped to an HTTP status by the API layer."""

    status_code: int
    message: str


async def create_session(db: AsyncSession, user: User, setup: InterviewSetup) -> InterviewSession:
    session = InterviewSession(
        user_id=user.id,
        status=SessionStatus.CREATED,
        role=setup.role,
        level=setup.level,
        mode=setup.mode,
        current_turn=0,
    )
    db.add(session)
    await db.flush()
    for kind, text in ((DocumentKind.CV, setup.cv_text), (DocumentKind.JD, setup.jd_text)):
        if text:
            db.add(
                SessionDocument(
                    session_id=session.id, kind=kind, source=DocumentSource.PASTE, text=text
                )
            )
    await db.commit()
    return session


async def get_owned_session(
    db: AsyncSession, user: User, session_id: uuid.UUID
) -> InterviewSession:
    session = await db.get(InterviewSession, session_id)
    # Same 404 for "missing" and "not yours": never reveal other users' sessions.
    if session is None or session.user_id != user.id:
        raise ServiceError(404, "Không tìm thấy phiên phỏng vấn.")
    return session


async def attach_document(
    db: AsyncSession,
    session: InterviewSession,
    kind: DocumentKind,
    *,
    data: bytes,
    filename: str,
    content_type: str | None,
) -> None:
    if session.status not in EDITABLE_STATUSES:
        raise ServiceError(409, "Không thể thay đổi tài liệu khi phiên đã bắt đầu.")
    try:
        text, source = extract_text(data, filename=filename, content_type=content_type)
    except DocumentError as exc:
        raise ServiceError(422, str(exc)) from exc
    limit = MAX_DOCUMENT_CHARS[kind]
    if len(text) > limit:
        raise ServiceError(422, f"{DOCUMENT_LABEL[kind]} quá dài (tối đa {limit:,} ký tự).")

    await db.execute(
        delete(SessionDocument).where(
            SessionDocument.session_id == session.id, SessionDocument.kind == kind
        )
    )
    db.add(
        SessionDocument(
            session_id=session.id,
            kind=kind,
            source=DocumentSource(source),
            filename=filename[:255] or None,
            text=text,
        )
    )
    # A new document makes any existing plan stale.
    await db.execute(
        delete(InterviewPlanRecord).where(InterviewPlanRecord.session_id == session.id)
    )
    session.status = SessionStatus.CREATED
    await db.commit()


async def _documents(
    db: AsyncSession, session_id: uuid.UUID
) -> dict[DocumentKind, SessionDocument]:
    rows = await db.scalars(select(SessionDocument).where(SessionDocument.session_id == session_id))
    return {doc.kind: doc for doc in rows}


async def prepare_session(db: AsyncSession, session: InterviewSession, preparer: Preparer) -> None:
    if session.status is SessionStatus.READY:
        return  # idempotent: the frozen plan already exists
    if session.status not in CLAIMABLE_STATUSES:
        raise ServiceError(409, "Phiên đang được lập kế hoạch hoặc đã bắt đầu.")

    claimed = await db.execute(
        update(InterviewSession)
        .where(
            InterviewSession.id == session.id,
            InterviewSession.status.in_(CLAIMABLE_STATUSES),
        )
        .values(status=SessionStatus.PREPARING)
    )
    await db.commit()
    if claimed.rowcount != 1:
        raise ServiceError(409, "Phiên đang được lập kế hoạch.")

    docs = await _documents(db, session.id)
    setup = InterviewSetup(
        role=session.role,
        level=session.level,
        mode=session.mode,
        cv_text=docs[DocumentKind.CV].text if DocumentKind.CV in docs else None,
        jd_text=docs[DocumentKind.JD].text if DocumentKind.JD in docs else None,
    )
    try:
        result = await preparer.run(setup, session_key=str(session.id))
    except SelectionError as exc:
        logger.error("Playbook selection failed for session %s: %s", session.id, exc)
        await _mark_failed(db, session.id)
        raise ServiceError(503, "Thư viện câu hỏi chưa sẵn sàng cho vị trí và cấp độ này.") from exc
    except Exception:
        logger.exception("Preparation failed for session %s", session.id)
        await _mark_failed(db, session.id)
        raise ServiceError(500, "Không lập được kế hoạch phỏng vấn. Vui lòng thử lại.") from None

    plan = result.plan
    await db.execute(
        delete(InterviewPlanRecord).where(InterviewPlanRecord.session_id == session.id)
    )
    db.add(
        InterviewPlanRecord(
            session_id=session.id,
            plan_json=plan.model_dump(mode="json"),
            plan_schema_version=plan.versions.plan_schema,
            role_playbook_id=plan.role_playbook.id,
            role_playbook_version=plan.role_playbook.version,
            selected_skills_json=[
                {"id": s.id, "version": s.version, "content_sha256": s.content_sha256}
                for s in plan.selected_skills
            ],
            catalog_version=plan.versions.catalog,
            rubric_version=plan.versions.rubric,
            planner_prompt_version=plan.versions.planner_prompt,
        )
    )
    analysis = result.analysis
    if DocumentKind.CV in docs and analysis.candidate is not None:
        docs[DocumentKind.CV].parsed_json = analysis.candidate.model_dump(mode="json")
    if DocumentKind.JD in docs and analysis.job is not None:
        docs[DocumentKind.JD].parsed_json = analysis.job.model_dump(mode="json")
    await db.execute(
        update(InterviewSession)
        .where(InterviewSession.id == session.id)
        .values(status=SessionStatus.READY)
    )
    await db.commit()
    logger.info(
        "Session %s prepared with %s (%d questions)",
        session.id,
        result.planner_model,
        len(plan.questions),
    )


async def _mark_failed(db: AsyncSession, session_id: uuid.UUID) -> None:
    await db.rollback()
    await db.execute(
        update(InterviewSession)
        .where(InterviewSession.id == session_id)
        .values(status=SessionStatus.FAILED)
    )
    await db.commit()


async def load_plan(db: AsyncSession, session_id: uuid.UUID) -> InterviewPlan | None:
    record = await db.get(InterviewPlanRecord, session_id)
    return InterviewPlan.model_validate(record.plan_json) if record else None


async def session_view(db: AsyncSession, session: InterviewSession) -> SessionView:
    await db.refresh(session)
    docs = await _documents(db, session.id)
    plan = await load_plan(db, session.id)
    report = await db.get(InterviewReportRecord, session.id)
    turns = await db.scalars(
        select(InterviewTurn)
        .where(InterviewTurn.session_id == session.id)
        .order_by(InterviewTurn.turn_no)
    )
    return SessionView(
        id=session.id,
        role=session.role,
        level=session.level,
        mode=session.mode,
        status=session.status,
        has_cv=DocumentKind.CV in docs,
        has_jd=DocumentKind.JD in docs,
        created_at=session.created_at,
        started_at=session.started_at,
        ended_at=session.ended_at,
        end_reason=session.end_reason,
        plan_preview=PlanPreview.from_plan(plan) if plan else None,
        turns=[
            TurnView(
                turn_no=t.turn_no,
                question_id=t.question_id,
                parent_question_id=t.parent_question_id,
                kind=t.kind,
                skill_id=t.skill_id,
                question_text=t.question_text,
                answer_text=t.answer_text,
                asked_at=t.asked_at,
                answered_at=t.answered_at,
            )
            for t in turns
        ],
        report_status=report.status if report else None,
    )


async def list_sessions(db: AsyncSession, user: User) -> list[SessionSummary]:
    sessions = list(
        await db.scalars(
            select(InterviewSession)
            .where(InterviewSession.user_id == user.id)
            .order_by(InterviewSession.created_at.desc())
            .limit(LIST_LIMIT)
        )
    )
    ids = [s.id for s in sessions]
    doc_kinds: dict[uuid.UUID, set[DocumentKind]] = {sid: set() for sid in ids}
    for doc in await db.scalars(select(SessionDocument).where(SessionDocument.session_id.in_(ids))):
        doc_kinds[doc.session_id].add(doc.kind)
    reports = {
        r.session_id: r
        for r in await db.scalars(
            select(InterviewReportRecord).where(InterviewReportRecord.session_id.in_(ids))
        )
    }
    summaries = []
    for s in sessions:
        report = reports.get(s.id)
        score = (report.report_json or {}).get("overall_score") if report else None
        summaries.append(
            SessionSummary(
                id=s.id,
                role=s.role,
                level=s.level,
                mode=s.mode,
                status=s.status,
                has_cv=DocumentKind.CV in doc_kinds[s.id],
                has_jd=DocumentKind.JD in doc_kinds[s.id],
                created_at=s.created_at,
                ended_at=s.ended_at,
                report_status=report.status if report else None,
                overall_score=score,
            )
        )
    return summaries


async def delete_session(db: AsyncSession, session: InterviewSession) -> None:
    await db.delete(session)  # documents, plan, turns, evaluations, report cascade in the DB
    await db.commit()
