"""POST-interview results. Unique keys make evaluation and report generation idempotent."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai.schemas.enums import EvaluationStatus, ReportStatus
from app.models.base import Base, UuidPrimaryKey, created_at_column, str_enum


class AnswerEvaluation(UuidPrimaryKey, Base):
    """Evaluation of one question thread (`EvaluationResult`), scored with the frozen rubric."""

    __tablename__ = "answer_evaluations"
    __table_args__ = (UniqueConstraint("session_id", "question_id"),)

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[str] = mapped_column(String(32), nullable=False)
    skill_id: Mapped[str] = mapped_column(String(64), nullable=False)
    skill_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[EvaluationStatus] = mapped_column(
        str_enum(EvaluationStatus, "evaluation_status"), nullable=False
    )
    weighted_score: Mapped[float | None] = mapped_column(Float)
    rubric_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    evaluator_prompt_version: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = created_at_column()


class InterviewReportRecord(Base):
    """Report job state + result. One row per session; retries update it in place."""

    __tablename__ = "interview_reports"

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="CASCADE"), primary_key=True
    )
    status: Mapped[ReportStatus] = mapped_column(
        str_enum(ReportStatus, "report_status"), nullable=False, default=ReportStatus.PENDING
    )
    report_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Sanitised error class/message only — never candidate content.
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
