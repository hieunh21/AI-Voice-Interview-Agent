"""Initial schema: users, sessions, optional documents, frozen plans, turns, evaluations, reports.

Revision ID: 0001
Revises:
Create Date: 2026-11-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _enum(name: str, *values: str) -> sa.Enum:
    # Frozen copy of the value lists at this revision (migrations must not import app enums).
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=32)


def _created_at() -> sa.Column:
    return sa.Column(
        "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )


def _session_fk() -> sa.Column:
    return sa.Column(
        "session_id",
        sa.Uuid(),
        sa.ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(320), unique=True),
        sa.Column("guest_token_hash", sa.String(64), unique=True),
        _created_at(),
    )

    op.create_table(
        "interview_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "status",
            _enum(
                "session_status",
                "created",
                "preparing",
                "ready",
                "in_progress",
                "completed",
                "failed",
            ),
            nullable=False,
        ),
        sa.Column(
            "role",
            _enum("role", "ai_engineer", "backend_developer", "data_engineer"),
            nullable=False,
        ),
        sa.Column("level", _enum("level", "intern", "fresher", "junior"), nullable=False),
        sa.Column("mode", _enum("mode", "demo", "standard"), nullable=False),
        sa.Column("current_turn", sa.Integer(), nullable=False),
        sa.Column(
            "end_reason",
            _enum("end_reason", "plan_completed", "user_ended", "max_turns", "time_budget"),
        ),
        _created_at(),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_interview_sessions_user_created", "interview_sessions", ["user_id", "created_at"]
    )

    op.create_table(
        "session_documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _session_fk(),
        sa.Column("kind", _enum("kind", "cv", "jd"), nullable=False),
        sa.Column("source", _enum("source", "paste", "pdf", "txt"), nullable=False),
        sa.Column("filename", sa.String(255)),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("parsed_json", postgresql.JSONB()),
        _created_at(),
        sa.UniqueConstraint("session_id", "kind"),
    )

    op.create_table(
        "interview_plans",
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("interview_sessions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("plan_json", postgresql.JSONB(), nullable=False),
        sa.Column("plan_schema_version", sa.String(32), nullable=False),
        sa.Column("role_playbook_id", sa.String(64), nullable=False),
        sa.Column("role_playbook_version", sa.String(32), nullable=False),
        sa.Column("selected_skills_json", postgresql.JSONB(), nullable=False),
        sa.Column("catalog_version", sa.String(32), nullable=False),
        sa.Column("rubric_version", sa.String(32), nullable=False),
        sa.Column("planner_prompt_version", sa.String(32), nullable=False),
        _created_at(),
    )

    op.create_table(
        "interview_turns",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _session_fk(),
        sa.Column("turn_no", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.String(32), nullable=False),
        sa.Column("parent_question_id", sa.String(32)),
        sa.Column("kind", _enum("kind", "main", "follow_up", "clarify"), nullable=False),
        sa.Column("skill_id", sa.String(64), nullable=False),
        sa.Column("skill_version", sa.String(32), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("answer_text", sa.Text()),
        sa.Column("answer_mode", _enum("answer_mode", "text", "voice")),
        sa.Column("answer_request_id", sa.String(64)),
        sa.Column("decision_json", postgresql.JSONB()),
        sa.Column(
            "asked_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("answered_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("session_id", "turn_no"),
        sa.UniqueConstraint("session_id", "answer_request_id"),
    )

    op.create_table(
        "answer_evaluations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _session_fk(),
        sa.Column("question_id", sa.String(32), nullable=False),
        sa.Column("skill_id", sa.String(64), nullable=False),
        sa.Column("skill_version", sa.String(32), nullable=False),
        sa.Column(
            "status",
            _enum("evaluation_status", "scored", "insufficient_evidence"),
            nullable=False,
        ),
        sa.Column("weighted_score", sa.Float()),
        sa.Column("rubric_json", postgresql.JSONB(), nullable=False),
        sa.Column("result_json", postgresql.JSONB(), nullable=False),
        sa.Column("evaluator_prompt_version", sa.String(32), nullable=False),
        _created_at(),
        sa.UniqueConstraint("session_id", "question_id"),
    )

    op.create_table(
        "interview_reports",
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("interview_sessions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "status",
            _enum("report_status", "pending", "processing", "completed", "failed"),
            nullable=False,
        ),
        sa.Column("report_json", postgresql.JSONB()),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text()),
        _created_at(),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("generated_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_table("interview_reports")
    op.drop_table("answer_evaluations")
    op.drop_table("interview_turns")
    op.drop_table("interview_plans")
    op.drop_table("session_documents")
    op.drop_index("ix_interview_sessions_user_created", table_name="interview_sessions")
    op.drop_table("interview_sessions")
    op.drop_table("users")
