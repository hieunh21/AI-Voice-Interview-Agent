"""Interview session tables. Every child row cascades on session delete (user data removal)."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai.schemas.enums import (
    AnswerMode,
    DocumentKind,
    DocumentSource,
    EndReason,
    InterviewMode,
    Level,
    Role,
    SessionStatus,
    TurnKind,
)
from app.models.base import Base, UuidPrimaryKey, created_at_column, str_enum


class InterviewSession(UuidPrimaryKey, Base):
    __tablename__ = "interview_sessions"
    __table_args__ = (Index("ix_interview_sessions_user_created", "user_id", "created_at"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[SessionStatus] = mapped_column(
        str_enum(SessionStatus, "session_status"), nullable=False, default=SessionStatus.CREATED
    )
    role: Mapped[Role] = mapped_column(str_enum(Role, "role"), nullable=False)
    level: Mapped[Level] = mapped_column(str_enum(Level, "level"), nullable=False)
    mode: Mapped[InterviewMode] = mapped_column(str_enum(InterviewMode, "mode"), nullable=False)
    current_turn: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    end_reason: Mapped[EndReason | None] = mapped_column(str_enum(EndReason, "end_reason"))
    created_at: Mapped[datetime] = created_at_column()
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SessionDocument(UuidPrimaryKey, Base):
    """Optional CV / JD for one session. Absent rows mean "not provided" — never fabricated."""

    __tablename__ = "session_documents"
    __table_args__ = (UniqueConstraint("session_id", "kind"),)

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[DocumentKind] = mapped_column(str_enum(DocumentKind, "kind"), nullable=False)
    source: Mapped[DocumentSource] = mapped_column(
        str_enum(DocumentSource, "source"), nullable=False
    )
    filename: Mapped[str | None] = mapped_column(String(255))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = created_at_column()


class InterviewPlanRecord(Base):
    """Frozen `InterviewPlan` (ai.schemas.interview); version columns denormalised for queries."""

    __tablename__ = "interview_plans"

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="CASCADE"), primary_key=True
    )
    plan_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    plan_schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    role_playbook_id: Mapped[str] = mapped_column(String(64), nullable=False)
    role_playbook_version: Mapped[str] = mapped_column(String(32), nullable=False)
    selected_skills_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    catalog_version: Mapped[str] = mapped_column(String(32), nullable=False)
    rubric_version: Mapped[str] = mapped_column(String(32), nullable=False)
    planner_prompt_version: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = created_at_column()


class InterviewTurn(UuidPrimaryKey, Base):
    """One question/answer exchange. `question_id` groups turns into question threads."""

    __tablename__ = "interview_turns"
    __table_args__ = (
        UniqueConstraint("session_id", "turn_no"),
        UniqueConstraint("session_id", "answer_request_id"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False
    )
    turn_no: Mapped[int] = mapped_column(Integer, nullable=False)
    question_id: Mapped[str] = mapped_column(String(32), nullable=False)
    parent_question_id: Mapped[str | None] = mapped_column(String(32))
    kind: Mapped[TurnKind] = mapped_column(str_enum(TurnKind, "kind"), nullable=False)
    skill_id: Mapped[str] = mapped_column(String(64), nullable=False)
    skill_version: Mapped[str] = mapped_column(String(32), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    answer_text: Mapped[str | None] = mapped_column(Text)
    answer_mode: Mapped[AnswerMode | None] = mapped_column(str_enum(AnswerMode, "answer_mode"))
    # Idempotency key of the POST /answer request that filled this turn (retries are no-ops).
    answer_request_id: Mapped[str | None] = mapped_column(String(64))
    # Validated AnswerDecision (no chain-of-thought is ever stored).
    decision_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    asked_at: Mapped[datetime] = created_at_column()
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
