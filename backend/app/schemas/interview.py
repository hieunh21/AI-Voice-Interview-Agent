"""API views of interview sessions.

The full `InterviewPlan` is never sent to the client: it contains expected points and rubric
notes, which would leak the answers. Clients get `PlanPreview` (topics, counts, time budget).
"""

import uuid
from datetime import datetime
from typing import Self

from pydantic import Field, model_validator

from ai.schemas.common import (
    ContractModel,
    Identifier,
    NonEmptyStr,
    QuestionId,
    SemVer,
    ThreadQuestionId,
)
from ai.schemas.enums import (
    EndReason,
    InputSource,
    InterviewMode,
    Level,
    ReportStatus,
    Role,
    SessionStatus,
    TurnKind,
)
from ai.schemas.evaluation import InterviewReport
from ai.schemas.interview import InterviewPlan


class VersionRef(ContractModel):
    id: Identifier
    version: SemVer


class PlanPreviewSkill(ContractModel):
    id: Identifier
    title: NonEmptyStr
    version: SemVer
    is_core: bool
    target_questions: int = Field(ge=1)
    reasons: list[str] = Field(default_factory=list)


class PlanPreview(ContractModel):
    role_playbook: VersionRef
    skills: list[PlanPreviewSkill] = Field(min_length=1)
    main_questions: int = Field(ge=1)
    max_turns: int = Field(ge=1)
    time_budget_minutes: int = Field(ge=1)
    input_sources: list[InputSource]
    warnings: list[str] = Field(default_factory=list)

    @classmethod
    def from_plan(cls, plan: InterviewPlan) -> Self:
        return cls(
            role_playbook=VersionRef(id=plan.role_playbook.id, version=plan.role_playbook.version),
            skills=[
                PlanPreviewSkill(
                    id=s.id,
                    title=s.title,
                    version=s.version,
                    is_core=s.is_core,
                    target_questions=s.target_questions,
                    reasons=s.reasons,
                )
                for s in plan.selected_skills
            ],
            main_questions=plan.limits.main_questions,
            max_turns=plan.limits.max_turns,
            time_budget_minutes=plan.limits.time_budget_minutes,
            input_sources=plan.input_sources,
            warnings=plan.warnings,
        )


class TurnView(ContractModel):
    turn_no: int = Field(ge=1)
    question_id: ThreadQuestionId
    parent_question_id: QuestionId | None = None
    kind: TurnKind
    skill_id: Identifier
    question_text: NonEmptyStr
    answer_text: str | None = None
    asked_at: datetime
    answered_at: datetime | None = None

    @model_validator(mode="after")
    def _check_thread(self) -> Self:
        is_main = self.kind is TurnKind.MAIN
        if is_main != (self.parent_question_id is None):
            raise ValueError(f"turn {self.turn_no}: only non-main turns have a parent_question_id")
        if not is_main and not self.question_id.startswith(f"{self.parent_question_id}."):
            raise ValueError(f"turn {self.turn_no}: question_id must extend its parent id")
        return self


class SessionSummary(ContractModel):
    id: uuid.UUID
    role: Role
    level: Level
    mode: InterviewMode
    status: SessionStatus
    has_cv: bool
    has_jd: bool
    created_at: datetime
    ended_at: datetime | None = None
    report_status: ReportStatus | None = None
    overall_score: float | None = None


class SessionView(ContractModel):
    id: uuid.UUID
    role: Role
    level: Level
    mode: InterviewMode
    status: SessionStatus
    has_cv: bool
    has_jd: bool
    created_at: datetime
    started_at: datetime | None = None
    ended_at: datetime | None = None
    end_reason: EndReason | None = None
    plan_preview: PlanPreview | None = None
    turns: list[TurnView] = Field(default_factory=list)
    report_status: ReportStatus | None = None

    @model_validator(mode="after")
    def _check_turns(self) -> Self:
        numbers = [t.turn_no for t in self.turns]
        if numbers != list(range(1, len(numbers) + 1)):
            raise ValueError("turns must be numbered 1..n in order")
        pending = [t.turn_no for t in self.turns if t.answer_text is None]
        if pending and pending != [numbers[-1]]:
            raise ValueError("only the latest turn may be unanswered")
        return self


class ReportResponse(ContractModel):
    status: ReportStatus
    report: InterviewReport | None = None
