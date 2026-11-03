"""Config contracts: role/level competency catalog and the shared rubric criteria."""

from typing import Self

from pydantic import Field, model_validator

from ai.schemas.common import SCORE_MAX, SCORE_MIN, ContractModel, Identifier, NonEmptyStr, SemVer
from ai.schemas.enums import Assessment, InterviewMode, Level, Role


class SkillBudget(ContractModel):
    min: int = Field(ge=1)
    max: int = Field(ge=1)


class ModeConfig(ContractModel):
    display_name: NonEmptyStr
    description: NonEmptyStr
    main_questions: int = Field(ge=1, le=20)
    max_followups_per_question: int = Field(ge=0, le=5)
    max_turns: int = Field(ge=1, le=40)
    time_budget_minutes: int = Field(ge=1, le=120)
    skills: SkillBudget

    @model_validator(mode="after")
    def _check_budget(self) -> Self:
        if self.skills.min > self.skills.max:
            raise ValueError("skills.min must be <= skills.max")
        if self.skills.max > self.main_questions:
            raise ValueError("skills.max must be <= main_questions (each skill needs a question)")
        if self.max_turns < self.main_questions:
            raise ValueError("max_turns must be >= main_questions")
        return self


class SkillWeight(ContractModel):
    weight: float = Field(gt=0, le=1)
    core: bool = False


class RoleLevelConfig(ContractModel):
    skills: dict[Identifier, SkillWeight] = Field(min_length=1)

    @property
    def core_skills(self) -> list[str]:
        return [skill_id for skill_id, cfg in self.skills.items() if cfg.core]


class RoleConfig(ContractModel):
    display_name: NonEmptyStr
    playbook: Identifier
    levels: dict[Level, RoleLevelConfig]


class LevelInfo(ContractModel):
    display_name: NonEmptyStr
    description: NonEmptyStr


class CompetencyCatalog(ContractModel):
    """`ai/config/competency_catalog.yaml` — the single source of truth for role → skill mapping."""

    version: SemVer
    modes: dict[InterviewMode, ModeConfig]
    levels: dict[Level, LevelInfo]
    cross_cutting_skills: list[Identifier]
    roles: dict[Role, RoleConfig]


class CriterionDefinition(ContractModel):
    name: NonEmptyStr
    applies_to: Assessment
    description: NonEmptyStr
    anchors: dict[int, NonEmptyStr]

    @model_validator(mode="after")
    def _check_anchors(self) -> Self:
        expected = set(range(SCORE_MIN, SCORE_MAX + 1))
        if set(self.anchors) != expected:
            raise ValueError(f"anchors must define every score {SCORE_MIN}..{SCORE_MAX}")
        return self


class RubricCriteriaCatalog(ContractModel):
    """`ai/config/rubric_criteria.yaml` — shared criteria with behaviourally anchored 1–5 scales."""

    version: SemVer
    criteria: dict[Identifier, CriterionDefinition] = Field(min_length=1)
