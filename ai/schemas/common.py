"""Shared constrained types and the base model for every data contract."""

import math
from collections.abc import Iterable
from typing import Annotated, Protocol

from pydantic import BaseModel, ConfigDict, StringConstraints

SEMVER_PATTERN = r"^\d+\.\d+\.\d+$"
IDENTIFIER_PATTERN = r"^[a-z][a-z0-9_]{1,63}$"

SemVer = Annotated[str, StringConstraints(pattern=SEMVER_PATTERN)]
Identifier = Annotated[str, StringConstraints(pattern=IDENTIFIER_PATTERN)]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
# Planned (main) questions: q_001, q_002, ...
QuestionId = Annotated[str, StringConstraints(pattern=r"^q_\d{3}$")]
# Turn-level ids inside a question thread: q_001, q_001.f1 (follow-up), q_001.c1 (clarify).
ThreadQuestionId = Annotated[str, StringConstraints(pattern=r"^q_\d{3}(\.[fc]\d{1,2})?$")]
NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

SCORE_MIN = 1
SCORE_MAX = 5
WEIGHT_TOLERANCE = 1e-6


class ContractModel(BaseModel):
    """Strict, immutable base: unknown fields are rejected so contracts cannot drift silently."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class Weighted(Protocol):
    @property
    def criterion_id(self) -> str: ...

    @property
    def weight(self) -> float: ...


def check_rubric_weights(criteria: Iterable[Weighted]) -> None:
    """Raise ValueError unless criterion ids are unique and weights sum to 1."""
    items = list(criteria)
    if not items:
        raise ValueError("rubric must contain at least one criterion")
    ids = [c.criterion_id for c in items]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise ValueError(f"duplicate rubric criteria: {', '.join(duplicates)}")
    total = math.fsum(c.weight for c in items)
    if abs(total - 1.0) > WEIGHT_TOLERANCE:
        raise ValueError(f"rubric weights must sum to 1.0 (got {total:.4f})")
