"""Report jobs: DB-backed state (pending → processing → completed | failed), no queue system.

- `ensure_report_row` is called in the same transaction that completes a session (idempotent).
- `ReportJobs.schedule` runs the evaluation as an asyncio task; a conditional UPDATE claims the
  job so it never runs twice concurrently.
- On startup, pending and stale processing jobs are re-queued (hosts that restart lose tasks).
- Results are written in one transaction: per-thread rows (unique per question) + the report.
"""

import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ai.evaluation.evaluator import AnsweredTurn, EvaluationError, Evaluator
from ai.prompts.evaluator import EVALUATOR_PROMPT_VERSION
from ai.schemas.enums import AnswerMode, ReportStatus
from ai.schemas.evaluation import InterviewReport
from app.db import Database
from app.models import AnswerEvaluation, InterviewReportRecord, InterviewTurn
from app.services.interviews import ServiceError, load_plan

logger = logging.getLogger(__name__)

STALE_AFTER = timedelta(minutes=10)
MAX_ATTEMPTS = 5


async def has_answers(db: AsyncSession, session_id: uuid.UUID) -> bool:
    count = await db.scalar(
        select(func.count())
        .select_from(InterviewTurn)
        .where(InterviewTurn.session_id == session_id, InterviewTurn.answer_text.is_not(None))
    )
    return bool(count)


async def ensure_report_row(db: AsyncSession, session_id: uuid.UUID) -> bool:
    """Create the pending report row if the session has answers. Returns True if one exists."""
    if not await has_answers(db, session_id):
        return False
    await db.execute(
        insert(InterviewReportRecord)
        .values(session_id=session_id, status=ReportStatus.PENDING, attempts=0)
        .on_conflict_do_nothing(index_elements=["session_id"])
    )
    return True


class ReportJobs:
    def __init__(self, database: Database, evaluator: Evaluator) -> None:
        self._db = database
        self._evaluator = evaluator
        self._tasks: set[asyncio.Task] = set()

    def schedule(self, session_id: uuid.UUID) -> None:
        task = asyncio.create_task(self._run(session_id), name=f"report-{session_id}")
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def wait_idle(self) -> None:
        """Wait for running jobs (used on shutdown and in tests)."""
        while self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)

    async def resume_pending(self) -> int:
        stale = datetime.now(UTC) - STALE_AFTER
        async with self._db.sessionmaker() as db:
            ids = list(
                await db.scalars(
                    select(InterviewReportRecord.session_id).where(
                        or_(
                            InterviewReportRecord.status == ReportStatus.PENDING,
                            (InterviewReportRecord.status == ReportStatus.PROCESSING)
                            & (InterviewReportRecord.started_at < stale),
                        ),
                        InterviewReportRecord.attempts < MAX_ATTEMPTS,
                    )
                )
            )
            if ids:
                await db.execute(
                    update(InterviewReportRecord)
                    .where(InterviewReportRecord.session_id.in_(ids))
                    .values(status=ReportStatus.PENDING)
                )
                await db.commit()
        for session_id in ids:
            self.schedule(session_id)
        return len(ids)

    async def _run(self, session_id: uuid.UUID) -> None:
        async with self._db.sessionmaker() as db:
            claimed = await db.execute(
                update(InterviewReportRecord)
                .where(
                    InterviewReportRecord.session_id == session_id,
                    InterviewReportRecord.status == ReportStatus.PENDING,
                )
                .values(
                    status=ReportStatus.PROCESSING,
                    attempts=InterviewReportRecord.attempts + 1,
                    started_at=datetime.now(UTC),
                    last_error=None,
                )
            )
            await db.commit()
            if claimed.rowcount != 1:
                return  # another worker has it, or it is already done
            try:
                await self._evaluate_and_store(db, session_id)
            except Exception as exc:
                await db.rollback()
                kind = type(exc).__name__
                message = str(exc)[:200] if isinstance(exc, EvaluationError) else ""
                logger.warning("Report for %s failed: %s %s", session_id, kind, message)
                await db.execute(
                    update(InterviewReportRecord)
                    .where(InterviewReportRecord.session_id == session_id)
                    .values(status=ReportStatus.FAILED, last_error=f"{kind}: {message}".strip(": "))
                )
                await db.commit()

    async def _evaluate_and_store(self, db: AsyncSession, session_id: uuid.UUID) -> None:
        plan = await load_plan(db, session_id)
        if plan is None:
            raise EvaluationError("session has no plan")
        rows = await db.scalars(
            select(InterviewTurn)
            .where(InterviewTurn.session_id == session_id, InterviewTurn.answer_text.is_not(None))
            .order_by(InterviewTurn.turn_no)
        )
        turns = [
            AnsweredTurn(
                turn_no=t.turn_no,
                question_id=t.question_id,
                parent_question_id=t.parent_question_id,
                kind=t.kind,
                question_text=t.question_text,
                answer_text=t.answer_text or "",
                from_voice=t.answer_mode is AnswerMode.VOICE,
            )
            for t in rows
        ]
        evaluation = await self._evaluator.evaluate(
            session_id=str(session_id), plan=plan, turns=turns
        )
        await db.execute(delete(AnswerEvaluation).where(AnswerEvaluation.session_id == session_id))
        for result in evaluation.results:
            question = plan.question(result.question_id)
            db.add(
                AnswerEvaluation(
                    session_id=session_id,
                    question_id=result.question_id,
                    skill_id=result.skill_id,
                    skill_version=result.skill_version,
                    status=result.status,
                    weighted_score=result.weighted_score,
                    rubric_json=[c.model_dump(mode="json") for c in question.rubric],
                    result_json=result.model_dump(mode="json"),
                    evaluator_prompt_version=EVALUATOR_PROMPT_VERSION,
                )
            )
        await db.execute(
            update(InterviewReportRecord)
            .where(InterviewReportRecord.session_id == session_id)
            .values(
                status=ReportStatus.COMPLETED,
                report_json=evaluation.report.model_dump(mode="json"),
                generated_at=datetime.now(UTC),
            )
        )
        await db.commit()
        logger.info(
            "Report for %s completed: %d question(s), overall %s",
            session_id,
            len(evaluation.results),
            evaluation.report.overall_score,
        )


async def get_report(
    db: AsyncSession, session_id: uuid.UUID
) -> tuple[ReportStatus, InterviewReport | None]:
    record = await db.get(InterviewReportRecord, session_id)
    if record is None:
        raise ServiceError(
            404, "Phiên này chưa có báo cáo (chưa kết thúc hoặc không có câu trả lời)."
        )
    report = InterviewReport.model_validate(record.report_json) if record.report_json else None
    return record.status, report


async def retry_report(db: AsyncSession, session_id: uuid.UUID) -> bool:
    """Re-queue a failed report. Returns True if a job should be scheduled."""
    result = await db.execute(
        update(InterviewReportRecord)
        .where(
            InterviewReportRecord.session_id == session_id,
            InterviewReportRecord.status == ReportStatus.FAILED,
        )
        .values(status=ReportStatus.PENDING)
    )
    await db.commit()
    return result.rowcount == 1
