"""Planner validation: the LLM proposes, the playbook decides what gets frozen."""

import random

import pytest
from helpers import CV_TEXT, JD_TEXT

from ai.nodes.planner import (
    DETERMINISTIC_MODEL,
    PlanInputs,
    assemble_plan,
    deterministic_drafts,
    max_personalised,
    validate_llm_drafts,
)
from ai.playbook_loader import load_library
from ai.playbook_selector import select_playbooks
from ai.prompts.planner import PlannedQuestionOut, PlannerOutput
from ai.schemas.documents import CandidateProfile, CandidateProject, DocumentAnalysis, JobSpec
from ai.schemas.enums import InterviewMode, Level, QuestionOrigin, Role
from ai.schemas.interview import InterviewSetup

LIBRARY = load_library()
ANALYSIS = DocumentAnalysis(
    candidate=CandidateProfile(
        skills=["Qdrant", "LangGraph"],
        projects=[
            CandidateProject(
                name="Chatbot nội quy", evidence="Chatbot hỏi đáp nội quy công ty dùng LangGraph"
            )
        ],
    ),
    job=JobSpec(required_skills=["RAG", "LangGraph"]),
    source="llm",
)


def _inputs(mode=InterviewMode.DEMO, cv=CV_TEXT, jd=None, analysis=ANALYSIS) -> PlanInputs:
    setup = InterviewSetup(
        role=Role.AI_ENGINEER, level=Level.FRESHER, mode=mode, cv_text=cv, jd_text=jd
    )
    selection = select_playbooks(
        LIBRARY, role=setup.role, level=setup.level, mode=setup.mode, allow_draft=True
    )
    return PlanInputs(library=LIBRARY, selection=selection, setup=setup, analysis=analysis)


def _q(skill_id, origin="seed", seed="", text="Câu hỏi đủ dài?", note="", expected=()):
    return PlannedQuestionOut(
        skill_id=skill_id,
        origin=origin,
        source_seed_id=seed,
        question_text=text,
        objective="obj",
        personalization_note=note,
        expected_points=list(expected),
        followup_hints=[],
    )


def _plan(drafts, inputs):
    return assemble_plan(drafts, inputs, planner_model="fake", warnings=[])


def test_seed_questions_use_frozen_seed_content_not_llm_content() -> None:
    inputs = _inputs()
    out = PlannerOutput(
        questions=[
            _q(
                "rag_systems", "seed_adapted", "rag_04", "Hybrid retrieval: khi nào và gộp thế nào?"
            ),
            _q("rag_systems", "seed", "rag_05", "LLM tự viết lại câu này"),
            _q("machine_learning", "seed", "ml_03"),
        ]
    )
    plan = _plan(validate_llm_drafts(out, inputs, random.Random(1)), inputs)
    q1, q2, _ = plan.questions
    seed4 = next(s for s in LIBRARY.skills["rag_systems"].seeds if s.id == "rag_04")
    seed5 = next(s for s in LIBRARY.skills["rag_systems"].seeds if s.id == "rag_05")
    assert q1.origin is QuestionOrigin.SEED_ADAPTED
    assert q1.question_text == "Hybrid retrieval: khi nào và gộp thế nào?"
    assert q1.expected_points == seed4.expected_points
    assert q1.scoring_caution == seed4.scoring_caution
    assert q2.question_text == seed5.question  # origin "seed" keeps the seed wording
    assert [r.criterion_id for r in q1.rubric] == [
        r.criterion_id for r in LIBRARY.skills["rag_systems"].rubric
    ]


def test_invalid_duplicate_and_surplus_proposals_are_dropped_and_slots_filled() -> None:
    inputs = _inputs()
    out = PlannerOutput(
        questions=[
            _q("rag_systems", "seed", "rag_99"),  # unknown seed
            _q("rag_systems", "seed", "rag_06"),  # junior-only seed at fresher level
            _q("deep_learning", "seed", "dl_01"),  # skill not selected
            _q("machine_learning", "seed", "ml_01"),
            _q("machine_learning", "seed", "ml_01"),  # duplicate seed
            _q("machine_learning", "seed", "ml_02"),  # surplus for this skill
        ]
    )
    drafts = validate_llm_drafts(out, inputs, random.Random(7))
    plan = _plan(drafts, inputs)
    assert [q.skill_id for q in plan.questions].count("rag_systems") == 2
    assert [q.skill_id for q in plan.questions].count("machine_learning") == 1
    seeds = [q.source_seed_id for q in plan.questions]
    assert len(seeds) == len(set(seeds))
    assert "rag_06" not in seeds


def test_cv_question_needs_grounding_in_the_validated_analysis() -> None:
    inputs = _inputs()
    grounded = _q(
        "rag_systems",
        "cv",
        text="Trong dự án Chatbot nội quy, bạn đánh giá retrieval thế nào?",
        note="CV: Chatbot nội quy",
        expected=["Recall@K", "bộ câu hỏi có nhãn"],
    )
    invented = _q(
        "rag_systems",
        "cv",
        text="Trong dự án hệ thống gợi ý phim, bạn xử lý cold start thế nào?",
        note="CV: hệ thống gợi ý phim",
        expected=["a", "b"],
    )
    plan = _plan(
        validate_llm_drafts(
            PlannerOutput(questions=[invented, grounded]), inputs, random.Random(1)
        ),
        inputs,
    )
    personalised = [q for q in plan.questions if q.origin is QuestionOrigin.CV]
    assert len(personalised) == 1
    assert "Chatbot nội quy" in personalised[0].question_text
    assert personalised[0].personalization_note


def test_cv_question_is_rejected_when_no_cv_was_provided() -> None:
    inputs = _inputs(cv=None)
    question = _q(
        "rag_systems",
        "cv",
        text="Trong dự án Chatbot nội quy, bạn làm gì?",
        note="CV: Chatbot nội quy",
        expected=["a", "b"],
    )
    plan = _plan(
        validate_llm_drafts(PlannerOutput(questions=[question]), inputs, random.Random(1)), inputs
    )
    assert all(q.origin is QuestionOrigin.SEED for q in plan.questions)


def test_personalised_questions_are_capped() -> None:
    inputs = _inputs(mode=InterviewMode.STANDARD, jd=JD_TEXT)
    many = [
        _q(
            "rag_systems",
            "jd",
            text=f"JD yêu cầu RAG với LangGraph — câu {i} của bạn là gì?",
            note="JD: RAG, LangGraph",
            expected=["a", "b"],
        )
        for i in range(5)
    ]
    plan = _plan(
        validate_llm_drafts(PlannerOutput(questions=many), inputs, random.Random(1)), inputs
    )
    personalised = [q for q in plan.questions if q.origin is QuestionOrigin.JD]
    assert len(personalised) <= max_personalised(plan.limits.main_questions)


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_deterministic_plan_is_valid_and_reproducible(seed: int) -> None:
    inputs = _inputs(mode=InterviewMode.STANDARD, cv=None, analysis=DocumentAnalysis())
    first = assemble_plan(
        deterministic_drafts(inputs, random.Random(seed)),
        inputs,
        planner_model=DETERMINISTIC_MODEL,
        warnings=[],
    )
    second = assemble_plan(
        deterministic_drafts(inputs, random.Random(seed)),
        inputs,
        planner_model=DETERMINISTIC_MODEL,
        warnings=[],
    )
    assert first == second
    assert first.versions.planner_model == "deterministic"
    assert set(first.rubric_criteria) >= {"technical_accuracy", "clarity", "decomposition"}
