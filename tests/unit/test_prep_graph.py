"""End-to-end PREP graph with a fake LLM that reads the real prompts."""

import asyncio

import pytest
from helpers import CV_TEXT, JD_TEXT, fake_llm

from ai.graphs.prep_graph import FALLBACK_WARNING, Preparer
from ai.llm.base import LLMQuotaExceeded
from ai.playbook_loader import load_library
from ai.schemas.enums import InputSource, QuestionOrigin
from ai.schemas.interview import InterviewSetup

LIBRARY = load_library()


def _run(preparer: Preparer, **setup):
    payload = {"role": "ai_engineer", "level": "fresher", "mode": "demo", **setup}
    return asyncio.run(preparer.run(InterviewSetup.model_validate(payload), session_key="s1"))


@pytest.mark.parametrize(
    ("cv", "jd"), [(None, None), (CV_TEXT, None), (None, JD_TEXT), (CV_TEXT, JD_TEXT)]
)
def test_all_four_document_combinations_produce_a_valid_plan(cv, jd) -> None:
    llm = fake_llm()
    result = _run(Preparer(LIBRARY, llm, allow_draft=True), cv_text=cv, jd_text=jd)
    plan = result.plan
    assert result.planner_model == "fake-llm"
    assert (InputSource.CV in plan.input_sources) == bool(cv)
    assert (InputSource.JD in plan.input_sources) == bool(jd)
    assert len(plan.questions) == plan.limits.main_questions
    if not cv and not jd:
        assert len(llm.calls) == 1  # no extraction call without documents


def test_cv_personalisation_uses_only_evidenced_projects() -> None:
    result = _run(Preparer(LIBRARY, fake_llm(), allow_draft=True), cv_text=CV_TEXT)
    candidate = result.analysis.candidate
    assert candidate is not None
    assert [p.name for p in candidate.projects] == ["Chatbot nội quy"]  # invented one dropped
    assert "Kotlin" not in candidate.skills
    cv_questions = [q for q in result.plan.questions if q.origin is QuestionOrigin.CV]
    assert len(cv_questions) == 1


def test_jd_out_of_scope_requirements_become_a_warning() -> None:
    result = _run(Preparer(LIBRARY, fake_llm(), allow_draft=True), jd_text=JD_TEXT)
    assert any("Kubernetes" in w for w in result.plan.warnings)


def test_jd_for_another_role_is_flagged_not_obeyed() -> None:
    result = _run(
        Preparer(LIBRARY, fake_llm(), allow_draft=True),
        role="backend_developer",
        jd_text=JD_TEXT,
    )
    assert result.plan.role.value == "backend_developer"
    assert any("khác vị trí bạn chọn" in w for w in result.plan.warnings)


def test_invalid_planner_output_is_retried_once() -> None:
    llm = fake_llm(planner_failures=1)
    result = _run(Preparer(LIBRARY, llm, allow_draft=True))
    assert result.planner_model == "fake-llm"
    assert len(llm.calls) == 2


def test_repeated_failures_fall_back_to_seed_plan_with_warning_when_documents_exist() -> None:
    llm = fake_llm(planner_failures=5)
    result = _run(Preparer(LIBRARY, llm, allow_draft=True), cv_text=CV_TEXT)
    assert result.planner_model == "deterministic"
    assert FALLBACK_WARNING in result.plan.warnings
    assert all(q.origin is QuestionOrigin.SEED for q in result.plan.questions)


def test_quota_errors_degrade_gracefully() -> None:
    llm = fake_llm(extraction_error=LLMQuotaExceeded("quota"))
    result = _run(Preparer(LIBRARY, llm, allow_draft=True), jd_text=JD_TEXT)
    assert result.analysis.source == "keywords"
    assert len(result.plan.questions) == 3


def test_failed_extraction_skips_the_planner_call() -> None:
    llm = fake_llm(extraction_error=LLMQuotaExceeded("quota"))
    result = _run(Preparer(LIBRARY, llm, allow_draft=True), cv_text=CV_TEXT)
    assert len(llm.calls) == 1  # no second wait on an unavailable LLM
    assert result.planner_model == "deterministic"
    assert FALLBACK_WARNING in result.plan.warnings


def test_no_llm_configured_builds_seed_plan_without_warning() -> None:
    result = _run(Preparer(LIBRARY, None, allow_draft=True))
    assert result.planner_model == "deterministic"
    assert result.plan.warnings == []
