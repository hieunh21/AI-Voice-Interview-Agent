"""Interview contracts: setup input, playbook selection, the frozen plan, and LIVE decisions."""

import re
from collections import Counter
from typing import Self

from pydantic import Field, field_validator, model_validator

from ai.schemas.catalog import CriterionDefinition
from ai.schemas.common import (
    ContractModel,
    Identifier,
    NonEmptyStr,
    QuestionId,
    SemVer,
    Sha256,
    check_rubric_weights,
)
from ai.schemas.enums import (
    AnswerQuality,
    Assessment,
    InputSource,
    InterviewMode,
    Level,
    NextAction,
    QuestionOrigin,
    Role,
)
from ai.schemas.playbook import PlaybookRef, RubricCriterion

PLAN_SCHEMA_VERSION = "1.0.0"
MAX_CV_CHARS = 20_000
MAX_JD_CHARS = 15_000

# Control characters except tab/newline/CR (PDF extraction and pastes often carry them).
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class InterviewSetup(ContractModel):
    """Body of `POST /api/interviews`. Role and level are required; CV/JD are optional."""

    role: Role
    level: Level
    mode: InterviewMode = InterviewMode.DEMO
    cv_text: str | None = Field(default=None, max_length=MAX_CV_CHARS)
    jd_text: str | None = Field(default=None, max_length=MAX_JD_CHARS)

    @field_validator("cv_text", "jd_text", mode="before")
    @classmethod
    def _normalise_document(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        cleaned = _CONTROL_CHARS.sub("", value).strip()
        return cleaned or None

    @property
    def input_sources(self) -> list[InputSource]:
        sources = [
            InputSource.ROLE_CONFIG,
            InputSource.ROLE_PLAYBOOK,
            InputSource.COMPETENCY_SKILLS,
        ]
        if self.cv_text:
            sources.append(InputSource.CV)
        if self.jd_text:
            sources.append(InputSource.JD)
        return sources


class InterviewLimits(ContractModel):
    main_questions: int = Field(ge=1)
    max_followups_per_question: int = Field(ge=0)
    max_turns: int = Field(ge=1)
    time_budget_minutes: int = Field(ge=1)


class SelectedSkill(ContractModel):
    id: Identifier
    title: NonEmptyStr
    version: SemVer
    content_sha256: Sha256
    is_core: bool
    target_questions: int = Field(ge=1)
    reasons: list[str] = Field(default_factory=list)


class PlaybookSelection(ContractModel):
    """Output of the rule-based PlaybookSelector (no LLM)."""

    role: Role
    level: Level
    mode: InterviewMode
    role_playbook: PlaybookRef
    skills: list[SelectedSkill] = Field(min_length=1)
    cross_cutting: list[PlaybookRef] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CrossCuttingSkill(ContractModel):
    """A skill scored over the whole transcript (communication, problem solving)."""

    id: Identifier
    title: NonEmptyStr
    version: SemVer
    content_sha256: Sha256
    rubric: list[RubricCriterion] = Field(min_length=1)


class PlannedQuestion(ContractModel):
    question_id: QuestionId
    skill_id: Identifier
    origin: QuestionOrigin
    source_seed_id: Identifier | None = None
    question_text: str = Field(min_length=5, max_length=1000)
    objective: NonEmptyStr
    personalization_note: str | None = None
    expected_points: list[NonEmptyStr] = Field(min_length=1)
    followup_hints: list[NonEmptyStr] = Field(default_factory=list)
    rubric: list[RubricCriterion] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_provenance(self) -> Self:
        seeded = self.origin in (QuestionOrigin.SEED, QuestionOrigin.SEED_ADAPTED)
        if seeded and self.source_seed_id is None:
            raise ValueError(f"{self.question_id}: seed-based questions need source_seed_id")
        if not seeded and not self.personalization_note:
            raise ValueError(f"{self.question_id}: CV/JD questions need a personalization_note")
        return self


class PlanVersions(ContractModel):
    plan_schema: SemVer = PLAN_SCHEMA_VERSION
    catalog: SemVer
    rubric: SemVer
    planner_prompt: SemVer


_REQUIRED_SOURCES = {
    InputSource.ROLE_CONFIG,
    InputSource.ROLE_PLAYBOOK,
    InputSource.COMPETENCY_SKILLS,
}


class InterviewPlan(ContractModel):
    """Immutable snapshot produced at PREP. LIVE and POST read only this, never the Markdown files.

    Rubric criterion definitions (with 1–5 anchors) are frozen once in `rubric_criteria`;
    each question carries its own weights and expected points.
    """

    role: Role
    level: Level
    mode: InterviewMode
    input_sources: list[InputSource]
    role_playbook: PlaybookRef
    selected_skills: list[SelectedSkill] = Field(min_length=1)
    cross_cutting_skills: list[CrossCuttingSkill] = Field(default_factory=list)
    rubric_criteria: dict[Identifier, CriterionDefinition] = Field(min_length=1)
    questions: list[PlannedQuestion] = Field(min_length=1)
    limits: InterviewLimits
    versions: PlanVersions
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        missing_sources = _REQUIRED_SOURCES - set(self.input_sources)
        if missing_sources:
            raise ValueError(f"input_sources missing {sorted(missing_sources)}")

        ids = [q.question_id for q in self.questions]
        expected_ids = [f"q_{i:03d}" for i in range(1, len(ids) + 1)]
        if ids != expected_ids:
            raise ValueError("question ids must be sequential (q_001, q_002, ...) in order")
        if len(self.questions) != self.limits.main_questions:
            raise ValueError("number of questions must equal limits.main_questions")

        skills = {s.id: s for s in self.selected_skills}
        if len(skills) != len(self.selected_skills):
            raise ValueError("selected_skills contains duplicates")
        per_skill = Counter(q.skill_id for q in self.questions)
        unknown = sorted(set(per_skill) - set(skills))
        if unknown:
            raise ValueError(f"questions reference unselected skills: {unknown}")
        for skill in self.selected_skills:
            if per_skill[skill.id] != skill.target_questions:
                raise ValueError(
                    f"skill {skill.id}: target_questions={skill.target_questions} "
                    f"but plan has {per_skill[skill.id]} question(s)"
                )

        for question in self.questions:
            self._check_rubric(question.question_id, question.rubric, Assessment.QUESTION)
        for skill in self.cross_cutting_skills:
            self._check_rubric(skill.id, skill.rubric, Assessment.CROSS_CUTTING)
        return self

    def _check_rubric(
        self, owner: str, rubric: list[RubricCriterion], applies_to: Assessment
    ) -> None:
        try:
            check_rubric_weights(rubric)
        except ValueError as exc:
            raise ValueError(f"{owner}: {exc}") from exc
        for criterion in rubric:
            definition = self.rubric_criteria.get(criterion.criterion_id)
            if definition is None:
                raise ValueError(f"{owner}: criterion {criterion.criterion_id} is not frozen")
            if definition.applies_to is not applies_to:
                raise ValueError(
                    f"{owner}: criterion {criterion.criterion_id} applies to "
                    f"{definition.applies_to.value}, not {applies_to.value}"
                )

    def question(self, question_id: str) -> PlannedQuestion:
        for q in self.questions:
            if q.question_id == question_id:
                return q
        raise KeyError(question_id)


class AnswerDecision(ContractModel):
    """Structured output of the LIVE answer analysis (one LLM call per answer).

    The backend validates it against limits; it never decides to finish the interview.
    `brief_note` is a short routing note, not chain-of-thought, and is never shown verbatim.
    """

    answer_quality: AnswerQuality
    covered_points: list[str] = Field(default_factory=list)
    missing_points: list[str] = Field(default_factory=list)
    next_action: NextAction
    question_text: str | None = Field(default=None, max_length=600)
    brief_note: str = Field(default="", max_length=300)

    @model_validator(mode="after")
    def _check_question(self) -> Self:
        needs_question = self.next_action in (NextAction.FOLLOW_UP, NextAction.CLARIFY)
        if needs_question and not (self.question_text and self.question_text.strip()):
            raise ValueError(f"{self.next_action.value} requires question_text")
        if not needs_question and self.question_text is not None:
            raise ValueError(
                "move_on must not carry question_text (the backend picks the next one)"
            )
        return self
