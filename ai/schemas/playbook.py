"""Contracts for parsed Markdown playbooks (role playbooks and competency skills)."""

from typing import Annotated, Literal, Self

from pydantic import AfterValidator, Field, StringConstraints, field_validator, model_validator

from ai.schemas.common import (
    ContractModel,
    Identifier,
    NonEmptyStr,
    SemVer,
    Sha256,
    check_rubric_weights,
)
from ai.schemas.enums import Assessment, Level, PlaybookStatus, Role

RolePlaybookId = Annotated[str, StringConstraints(pattern=r"^role_[a-z][a-z0-9_]*$")]


def _unique_levels(levels: list[Level]) -> list[Level]:
    if len(set(levels)) != len(levels):
        raise ValueError("levels must not contain duplicates")
    return levels


UniqueLevels = Annotated[list[Level], Field(min_length=1), AfterValidator(_unique_levels)]


class PlaybookRef(ContractModel):
    """Immutable pointer to the exact content a plan was built from."""

    id: Identifier
    version: SemVer
    content_sha256: Sha256


class RolePlaybookMeta(ContractModel):
    id: RolePlaybookId
    kind: Literal["role_playbook"]
    version: SemVer
    role: Role
    levels: UniqueLevels
    status: PlaybookStatus


class CompetencySkillMeta(ContractModel):
    id: Identifier
    kind: Literal["competency_skill"]
    version: SemVer
    assessment: Assessment = Assessment.QUESTION
    levels: UniqueLevels
    keywords: list[NonEmptyStr] = Field(default_factory=list)
    status: PlaybookStatus

    @field_validator("keywords")
    @classmethod
    def _normalise_keywords(cls, keywords: list[str]) -> list[str]:
        return list(dict.fromkeys(k.lower() for k in keywords))


class QuestionSeed(ContractModel):
    id: Identifier
    question: NonEmptyStr
    levels: UniqueLevels
    objective: NonEmptyStr
    expected_points: list[NonEmptyStr] = Field(min_length=2)
    followup_probes: list[NonEmptyStr] = Field(min_length=1)
    # A common wrong answer the evaluator must not reward (frozen into the plan).
    scoring_caution: str | None = None


class RubricCriterion(ContractModel):
    """A weighted criterion as used by one skill (definitions live in rubric_criteria.yaml)."""

    criterion_id: Identifier
    weight: float = Field(gt=0, le=1)
    note: str | None = None


class RolePlaybook(ContractModel):
    meta: RolePlaybookMeta
    title: NonEmptyStr
    sections: dict[str, str]
    level_guidance: dict[Level, str]
    path: str
    content_sha256: Sha256

    @property
    def ref(self) -> PlaybookRef:
        return PlaybookRef(
            id=self.meta.id, version=self.meta.version, content_sha256=self.content_sha256
        )


class CompetencySkill(ContractModel):
    meta: CompetencySkillMeta
    title: NonEmptyStr
    sections: dict[str, str]
    level_guidance: dict[Level, str]
    seeds: list[QuestionSeed]
    rubric: list[RubricCriterion]
    references: list[str]
    path: str
    content_sha256: Sha256

    @model_validator(mode="after")
    def _check(self) -> Self:
        check_rubric_weights(self.rubric)
        return self

    @property
    def ref(self) -> PlaybookRef:
        return PlaybookRef(
            id=self.meta.id, version=self.meta.version, content_sha256=self.content_sha256
        )

    def seeds_for_level(self, level: Level) -> list[QuestionSeed]:
        return [seed for seed in self.seeds if level in seed.levels]
