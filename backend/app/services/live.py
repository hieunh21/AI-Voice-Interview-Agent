"""LIVE use-cases: start, answer, finish.

`submit_answer` runs in one transaction holding a row lock on the session (FOR UPDATE NOWAIT):
- a concurrent submission for the same session fails fast with 409 instead of double-processing;
- if anything fails before commit (LLM crash, restart), nothing is persisted and the client can
  safely retry with the same request_id;
- a retry of an already-processed request_id is a no-op (idempotency);
- an answer for a question that is no longer pending (stale `turn_no`) is rejected.
"""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from ai.graphs.interview_graph import Interviewer
from ai.live_rules import NextTurn, TurnRecord, first_turn
from ai.prompts.interviewer import LIVE_PROMPT_VERSION
from ai.schemas.enums import AnswerMode, EndReason, SessionStatus
from ai.schemas.interview import InterviewPlan
from app.models import InterviewSession, InterviewTurn
from app.services.interviews import ServiceError, load_plan

logger = logging.getLogger(__name__)

_LOCK_NOT_AVAILABLE = "55P03"


def _now() -> datetime:
    return datetime.now(UTC)


def _is_lock_conflict(exc: DBAPIError) -> bool:
    orig = exc.orig
    code = getattr(orig, "pgcode", None) or getattr(orig, "sqlstate", None)
    cause = getattr(orig, "__cause__", None)
    return (code or getattr(cause, "sqlstate", None)) == _LOCK_NOT_AVAILABLE


def _skill_version(plan: InterviewPlan, skill_id: str) -> str:
    return next(s.version for s in plan.selected_skills if s.id == skill_id)


def _turn_row(
    session_id: uuid.UUID, turn_no: int, turn: NextTurn, plan: InterviewPlan
) -> InterviewTurn:
    return InterviewTurn(
        session_id=session_id,
        turn_no=turn_no,
        question_id=turn.question_id,
        parent_question_id=turn.parent_question_id,
        kind=turn.kind,
        skill_id=turn.skill_id,
        skill_version=_skill_version(plan, turn.skill_id),
        question_text=turn.question_text,
        asked_at=_now(),
    )


async def _require_plan(db: AsyncSession, session: InterviewSession) -> InterviewPlan:
    plan = await load_plan(db, session.id)
    if plan is None:
        raise ServiceError(409, "Phiên chưa có kế hoạch phỏng vấn.")
    return plan


async def start_interview(db: AsyncSession, session: InterviewSession) -> None:
    if session.status is SessionStatus.IN_PROGRESS:
        return  # idempotent
    if session.status is not SessionStatus.READY:
        raise ServiceError(409, "Phiên chưa sẵn sàng để bắt đầu.")
    plan = await _require_plan(db, session)
    claimed = await db.execute(
        update(InterviewSession)
        .where(InterviewSession.id == session.id, InterviewSession.status == SessionStatus.READY)
        .values(status=SessionStatus.IN_PROGRESS, started_at=_now(), current_turn=1)
    )
    if claimed.rowcount != 1:
        await db.rollback()
        return  # a concurrent start won; the caller re-reads the session
    db.add(_turn_row(session.id, 1, first_turn(plan), plan))
    await db.commit()


async def submit_answer(
    db: AsyncSession,
    session: InterviewSession,
    interviewer: Interviewer,
    *,
    request_id: str,
    turn_no: int,
    answer_text: str,
) -> None:
    try:
        locked = await db.scalar(
            select(InterviewSession)
            .where(InterviewSession.id == session.id)
            .with_for_update(nowait=True)
            .execution_options(populate_existing=True)
        )
    except DBAPIError as exc:
        await db.rollback()
        if _is_lock_conflict(exc):
            raise ServiceError(409, "Câu trả lời trước đang được xử lý, vui lòng đợi.") from None
        raise
    assert locked is not None

    already = await db.scalar(
        select(InterviewTurn.id).where(
            InterviewTurn.session_id == session.id, InterviewTurn.answer_request_id == request_id
        )
    )
    if already is not None:
        await db.rollback()
        return  # retry of a processed request: no-op

    if locked.status is not SessionStatus.IN_PROGRESS:
        raise ServiceError(409, "Phiên phỏng vấn không còn diễn ra.")
    turns = list(
        await db.scalars(
            select(InterviewTurn)
            .where(InterviewTurn.session_id == session.id)
            .order_by(InterviewTurn.turn_no)
        )
    )
    pending = turns[-1] if turns and turns[-1].answer_text is None else None
    if pending is None:
        raise ServiceError(409, "Không có câu hỏi nào đang chờ trả lời.")
    if pending.turn_no != turn_no:
        raise ServiceError(409, "Câu hỏi đã thay đổi. Hãy tải lại trang.")

    now = _now()
    pending.answer_text = answer_text
    pending.answer_mode = AnswerMode.TEXT
    pending.answer_request_id = request_id
    pending.answered_at = now

    plan = await _require_plan(db, session)
    records = [
        TurnRecord(
            turn_no=t.turn_no,
            question_id=t.question_id,
            parent_question_id=t.parent_question_id,
            kind=t.kind,
            skill_id=t.skill_id,
            question_text=t.question_text,
            answer_text=t.answer_text,
        )
        for t in turns
    ]
    started_at = locked.started_at or now
    result = await interviewer.next_step(plan, records, (now - started_at).total_seconds())
    outcome = result.outcome
    pending.decision_json = {
        "decision": result.decision.model_dump(mode="json"),
        "source": result.source,
        "model": result.model_id,
        "action": outcome.action,
        "overridden": outcome.overridden,
        "latency_ms": result.latency_ms,
        "prompt_version": LIVE_PROMPT_VERSION,
    }

    if outcome.next_turn is not None:
        db.add(_turn_row(session.id, pending.turn_no + 1, outcome.next_turn, plan))
        locked.current_turn = pending.turn_no + 1
    else:
        locked.status = SessionStatus.COMPLETED
        locked.ended_at = now
        locked.end_reason = outcome.end_reason
    await db.commit()
    logger.info(
        "Session %s turn %d → %s (%s, %d ms)",
        session.id,
        pending.turn_no,
        outcome.action,
        result.source,
        result.latency_ms,
    )


async def finish_interview(db: AsyncSession, session: InterviewSession) -> None:
    if session.status is SessionStatus.COMPLETED:
        return  # idempotent
    if session.status is not SessionStatus.IN_PROGRESS:
        raise ServiceError(409, "Chỉ kết thúc được phiên đang diễn ra.")
    await db.execute(
        update(InterviewSession)
        .where(
            InterviewSession.id == session.id,
            InterviewSession.status == SessionStatus.IN_PROGRESS,
        )
        .values(status=SessionStatus.COMPLETED, ended_at=_now(), end_reason=EndReason.USER_ENDED)
    )
    await db.commit()
