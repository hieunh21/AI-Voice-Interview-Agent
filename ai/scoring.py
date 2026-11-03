"""Deterministic score aggregation used by POST. The LLM scores criteria; numbers are computed here.

- question score = Σ weight × criterion score (frozen rubric of that question)
- skill score    = mean of its scored question threads (insufficient-evidence threads excluded)
- overall score  = catalog-weighted mean over skills that have a score, weights renormalised
All values are rounded to 2 decimals at each step so reports are reproducible.
"""

import math
import statistics
from collections.abc import Iterable, Mapping, Sequence

from ai.schemas.common import check_rubric_weights
from ai.schemas.playbook import RubricCriterion

_DECIMALS = 2


def weighted_score(scores: Mapping[str, int], rubric: Sequence[RubricCriterion]) -> float:
    check_rubric_weights(rubric)
    missing = sorted({c.criterion_id for c in rubric} - set(scores))
    if missing:
        raise ValueError(f"missing scores for criteria: {missing}")
    return round(math.fsum(c.weight * scores[c.criterion_id] for c in rubric), _DECIMALS)


def skill_score(question_scores: Iterable[float | None]) -> float | None:
    values = [score for score in question_scores if score is not None]
    return round(statistics.fmean(values), _DECIMALS) if values else None


def overall_score(
    skill_scores: Mapping[str, float | None], skill_weights: Mapping[str, float]
) -> float | None:
    assessed = {skill: score for skill, score in skill_scores.items() if score is not None}
    total_weight = math.fsum(skill_weights[skill] for skill in assessed)
    if not assessed or total_weight == 0:
        return None
    weighted = math.fsum(skill_weights[skill] * score for skill, score in assessed.items())
    return round(weighted / total_weight, _DECIMALS)
