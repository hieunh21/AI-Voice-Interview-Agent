"""POST contracts: per-question-thread evaluation and the aggregated report."""

from datetime import datetime
from typing import Self

from pydantic import Field, model_validator

from ai.schemas.common import (
    SCORE_MAX,
    SCORE_MIN,
    ContractModel,
    Identifier,
    NonEmptyStr,
    QuestionId,
    SemVer,
)
from ai.schemas.enums import EvaluationStatus, InterviewMode, Level, Role

DISCLAIMER = (
    "Đây là công cụ luyện tập. Kết quả không phải đánh giá tuyển dụng chính thức và chỉ dựa trên "
    "nội dung transcript bạn đã xác nhận."
)


class EvidenceQuote(ContractModel):
    """A verbatim excerpt of the candidate's answer in turn `turn_no` (checked after generation)."""

    turn_no: int = Field(ge=1)
    quote: str = Field(min_length=1, max_length=500)


class CriterionScore(ContractModel):
    criterion_id: Identifier
    score: int | None = Field(default=None, ge=SCORE_MIN, le=SCORE_MAX)
    rationale: NonEmptyStr
    evidence: list[EvidenceQuote] = Field(default_factory=list)

    @model_validator(mode="after")
    def _scored_needs_evidence(self) -> Self:
        if self.score is not None and not self.evidence:
            raise ValueError(f"{self.criterion_id}: a score must cite at least one evidence quote")
        return self


class EvaluationResult(ContractModel):
    """Evaluation of one question thread (main question + its follow-ups/clarifications)."""

    question_id: QuestionId
    skill_id: Identifier
    skill_version: SemVer
    status: EvaluationStatus
    turn_nos: list[int] = Field(min_length=1)
    criteria: list[CriterionScore] = Field(min_length=1)
    weighted_score: float | None = Field(default=None, ge=SCORE_MIN, le=SCORE_MAX)
    covered_points: list[str] = Field(default_factory=list)
    missed_points: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    improvement_suggestion: str = ""

    @model_validator(mode="after")
    def _check_status(self) -> Self:
        scored = [c.score is not None for c in self.criteria]
        if self.status is EvaluationStatus.SCORED:
            if not all(scored) or self.weighted_score is None:
                raise ValueError(f"{self.question_id}: scored results need every criterion scored")
        elif any(scored) or self.weighted_score is not None:
            raise ValueError(f"{self.question_id}: insufficient_evidence results carry no scores")
        cited = {e.turn_no for c in self.criteria for e in c.evidence}
        if not cited <= set(self.turn_nos):
            raise ValueError(f"{self.question_id}: evidence cites turns outside the thread")
        return self


class SkillScore(ContractModel):
    skill_id: Identifier
    skill_version: SemVer
    score: float | None = Field(default=None, ge=SCORE_MIN, le=SCORE_MAX)
    question_ids: list[QuestionId] = Field(min_length=1)
    summary: str = ""


class CrossCuttingResult(ContractModel):
    skill_id: Identifier
    skill_version: SemVer
    criteria: list[CriterionScore] = Field(min_length=1)
    summary: str = ""


class ReportVersions(ContractModel):
    rubric: SemVer
    evaluator_prompt: SemVer
    evaluator_model: str | None = None


class InterviewReport(ContractModel):
    session_id: str
    role: Role
    level: Level
    mode: InterviewMode
    overall_score: float | None = Field(default=None, ge=SCORE_MIN, le=SCORE_MAX)
    skill_scores: list[SkillScore]
    cross_cutting: list[CrossCuttingResult] = Field(default_factory=list)
    questions: list[EvaluationResult] = Field(min_length=1)
    top_strengths: list[str] = Field(default_factory=list)
    priority_improvements: list[str] = Field(default_factory=list)
    study_topics: list[str] = Field(default_factory=list)
    versions: ReportVersions
    disclaimer: str = DISCLAIMER
    generated_at: datetime

    @model_validator(mode="after")
    def _check_questions(self) -> Self:
        ids = [q.question_id for q in self.questions]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate question results")
        known = set(ids)
        for skill in self.skill_scores:
            unknown = set(skill.question_ids) - known
            if unknown:
                raise ValueError(f"{skill.skill_id}: unknown question ids {sorted(unknown)}")
        return self
