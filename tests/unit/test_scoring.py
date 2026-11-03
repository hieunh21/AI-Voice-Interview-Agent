import pytest

from ai.schemas.playbook import RubricCriterion
from ai.scoring import overall_score, skill_score, weighted_score

RUBRIC = [
    RubricCriterion(criterion_id="technical_accuracy", weight=0.40),
    RubricCriterion(criterion_id="completeness", weight=0.25),
    RubricCriterion(criterion_id="reasoning", weight=0.20),
    RubricCriterion(criterion_id="practical_examples", weight=0.15),
]


def test_weighted_score() -> None:
    scores = {"technical_accuracy": 4, "completeness": 3, "reasoning": 4, "practical_examples": 3}
    assert weighted_score(scores, RUBRIC) == 3.6


def test_weighted_score_requires_every_criterion() -> None:
    with pytest.raises(ValueError, match="missing scores"):
        weighted_score({"technical_accuracy": 4}, RUBRIC)


def test_skill_score_ignores_insufficient_evidence() -> None:
    assert skill_score([2.85, None, 2.25]) == 2.55
    assert skill_score([None]) is None


def test_overall_score_renormalises_over_assessed_skills() -> None:
    weights = {"databases": 0.30, "system_design": 0.30, "api_design": 0.25}
    scores = {"databases": 4.15, "system_design": None, "api_design": 3.4}
    assert overall_score(scores, weights) == 3.81
    assert overall_score({"databases": None}, weights) is None
