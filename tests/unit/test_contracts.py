"""Behaviour of the core data contracts (setup, plan, LIVE decision, evaluation)."""

import copy
from typing import Any

import pytest
from pydantic import ValidationError

from ai.playbook_loader import load_library
from ai.schemas import (
    AnswerDecision,
    EvaluationResult,
    InterviewPlan,
    InterviewSetup,
)
from ai.schemas.enums import InputSource, InterviewMode
from ai.schemas.interview import MAX_CV_CHARS

SHA = "a" * 64
QUESTION_RUBRIC = [
    {"criterion_id": "technical_accuracy", "weight": 0.40},
    {"criterion_id": "completeness", "weight": 0.25},
    {"criterion_id": "reasoning", "weight": 0.20},
    {"criterion_id": "practical_examples", "weight": 0.15},
]


def _question(question_id: str, skill_id: str) -> dict[str, Any]:
    return {
        "question_id": question_id,
        "skill_id": skill_id,
        "origin": "seed",
        "source_seed_id": f"{skill_id}_01",
        "question_text": "Overfitting là gì và bạn phát hiện nó thế nào?",
        "objective": "Hiểu overfitting",
        "expected_points": ["định nghĩa", "so sánh train/validation"],
        "followup_hints": ["cross-validation"],
        "rubric": copy.deepcopy(QUESTION_RUBRIC),
    }


@pytest.fixture(scope="module")
def criteria() -> dict[str, Any]:
    catalog = load_library().criteria
    assert catalog is not None
    return {key: value.model_dump(mode="json") for key, value in catalog.criteria.items()}


@pytest.fixture
def plan_data(criteria: dict[str, Any]) -> dict[str, Any]:
    return {
        "role": "ai_engineer",
        "level": "fresher",
        "mode": "demo",
        "input_sources": ["role_config", "role_playbook", "competency_skills"],
        "role_playbook": {"id": "role_ai_engineer", "version": "1.0.0", "content_sha256": SHA},
        "selected_skills": [
            {
                "id": "machine_learning",
                "title": "Machine Learning",
                "version": "1.0.0",
                "content_sha256": SHA,
                "is_core": True,
                "target_questions": 1,
            },
            {
                "id": "rag_systems",
                "title": "RAG Systems",
                "version": "1.0.0",
                "content_sha256": SHA,
                "is_core": True,
                "target_questions": 2,
            },
        ],
        "cross_cutting_skills": [
            {
                "id": "communication",
                "title": "Communication",
                "version": "1.0.0",
                "content_sha256": SHA,
                "rubric": [
                    {"criterion_id": "clarity", "weight": 0.6},
                    {"criterion_id": "structure", "weight": 0.4},
                ],
            }
        ],
        "rubric_criteria": criteria,
        "questions": [
            _question("q_001", "machine_learning"),
            _question("q_002", "rag_systems"),
            _question("q_003", "rag_systems"),
        ],
        "limits": {
            "main_questions": 3,
            "max_followups_per_question": 1,
            "max_turns": 6,
            "time_budget_minutes": 12,
        },
        "versions": {"catalog": "1.0.0", "rubric": "1.0.0", "planner_prompt": "1.0.0"},
    }


# ---------------------------------------------------------------- InterviewSetup


def test_setup_needs_only_role_and_level() -> None:
    setup = InterviewSetup.model_validate({"role": "ai_engineer", "level": "fresher"})
    assert setup.mode is InterviewMode.DEMO
    assert setup.cv_text is None
    assert setup.jd_text is None
    assert setup.input_sources == [
        InputSource.ROLE_CONFIG,
        InputSource.ROLE_PLAYBOOK,
        InputSource.COMPETENCY_SKILLS,
    ]


@pytest.mark.parametrize(
    "payload",
    [
        {"level": "fresher"},
        {"role": "ai_engineer"},
        {"role": "frontend_developer", "level": "fresher"},
        {"role": "ai_engineer", "level": "senior"},
        {"role": "ai_engineer", "level": "fresher", "unexpected": True},
    ],
)
def test_setup_rejects_missing_or_unsupported_values(payload: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        InterviewSetup.model_validate(payload)


def test_setup_treats_blank_documents_as_absent_and_strips_control_chars() -> None:
    setup = InterviewSetup.model_validate(
        {
            "role": "data_engineer",
            "level": "junior",
            "cv_text": "  \n\t ",
            "jd_text": "Yêu\x00 cầu SQL ",
        }
    )
    assert setup.cv_text is None
    assert setup.jd_text == "Yêu cầu SQL"
    assert InputSource.JD in setup.input_sources
    assert InputSource.CV not in setup.input_sources


def test_setup_limits_document_length() -> None:
    with pytest.raises(ValidationError):
        InterviewSetup.model_validate(
            {"role": "ai_engineer", "level": "intern", "cv_text": "x" * (MAX_CV_CHARS + 1)}
        )


# ---------------------------------------------------------------- InterviewPlan


def test_valid_plan(plan_data: dict[str, Any]) -> None:
    plan = InterviewPlan.model_validate(plan_data)
    assert plan.question("q_002").skill_id == "rag_systems"
    assert plan.versions.plan_schema == "1.0.0"
    assert plan.rubric_criteria["technical_accuracy"].anchors[5]


def _broken(plan_data: dict[str, Any], mutate) -> dict[str, Any]:
    data = copy.deepcopy(plan_data)
    mutate(data)
    return data


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda d: d["questions"][1].update(question_id="q_005"), "sequential"),
        (lambda d: d["limits"].update(main_questions=4), "main_questions"),
        (lambda d: d["selected_skills"][0].update(target_questions=2), "target_questions"),
        (lambda d: d["questions"][0].update(skill_id="deep_learning"), "unselected"),
        (lambda d: d["questions"][0]["rubric"][0].update(weight=0.5), "sum to 1.0"),
        (lambda d: d["rubric_criteria"].pop("reasoning"), "not frozen"),
        (
            lambda d: d["questions"][0]["rubric"][3].update(criterion_id="clarity"),
            "applies to cross_cutting",
        ),
        (lambda d: d["questions"][0].update(source_seed_id=None), "source_seed_id"),
        (lambda d: d["questions"][0].update(origin="cv"), "personalization_note"),
        (lambda d: d.update(input_sources=["cv"]), "input_sources"),
    ],
)
def test_plan_rejects_inconsistencies(plan_data: dict[str, Any], mutate, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        InterviewPlan.model_validate(_broken(plan_data, mutate))


def test_plan_is_immutable(plan_data: dict[str, Any]) -> None:
    plan = InterviewPlan.model_validate(plan_data)
    with pytest.raises(ValidationError):
        plan.mode = InterviewMode.STANDARD  # type: ignore[misc]


# ---------------------------------------------------------------- AnswerDecision


def test_follow_up_requires_question_text() -> None:
    with pytest.raises(ValidationError, match="requires question_text"):
        AnswerDecision.model_validate({"answer_quality": "partial", "next_action": "follow_up"})


def test_move_on_must_not_carry_a_question() -> None:
    with pytest.raises(ValidationError, match="move_on"):
        AnswerDecision.model_validate(
            {"answer_quality": "strong", "next_action": "move_on", "question_text": "Câu tiếp?"}
        )


def test_valid_follow_up_decision() -> None:
    decision = AnswerDecision.model_validate(
        {
            "answer_quality": "partial",
            "missing_points": ["fusion"],
            "next_action": "follow_up",
            "question_text": "Bạn gộp kết quả hai bên thế nào?",
        }
    )
    assert decision.missing_points == ["fusion"]


# ---------------------------------------------------------------- EvaluationResult


def _evaluation(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "question_id": "q_001",
        "skill_id": "rag_systems",
        "skill_version": "1.0.0",
        "status": "scored",
        "turn_nos": [1, 2],
        "weighted_score": 3.5,
        "criteria": [
            {
                "criterion_id": "technical_accuracy",
                "score": 4,
                "rationale": "Đúng khái niệm.",
                "evidence": [{"turn_no": 1, "quote": "BM25 khớp chính xác"}],
            }
        ],
    }
    data.update(overrides)
    return data


def test_scored_evaluation_is_valid() -> None:
    assert EvaluationResult.model_validate(_evaluation()).weighted_score == 3.5


def test_score_without_evidence_is_rejected() -> None:
    data = _evaluation()
    data["criteria"][0]["evidence"] = []
    with pytest.raises(ValidationError, match="evidence"):
        EvaluationResult.model_validate(data)


def test_evidence_must_come_from_the_thread() -> None:
    data = _evaluation()
    data["criteria"][0]["evidence"][0]["turn_no"] = 7
    with pytest.raises(ValidationError, match="outside the thread"):
        EvaluationResult.model_validate(data)


def test_insufficient_evidence_carries_no_scores() -> None:
    with pytest.raises(ValidationError, match="no scores"):
        EvaluationResult.model_validate(_evaluation(status="insufficient_evidence"))
    data = _evaluation(status="insufficient_evidence", weighted_score=None)
    data["criteria"][0].update(score=None, evidence=[])
    assert EvaluationResult.model_validate(data).weighted_score is None
