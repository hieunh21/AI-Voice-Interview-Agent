import pytest

from ai.playbook_loader import load_library
from ai.playbook_selector import (
    DocumentSignals,
    SelectionError,
    allocate_questions,
    keyword_hits,
    select_playbooks,
    unmatched_requirements,
)
from ai.schemas.enums import InterviewMode, Level, Role

LIBRARY = load_library()


def _select(role, level, mode, signals=None, allow_draft=True):
    return select_playbooks(
        LIBRARY,
        role=Role(role),
        level=Level(level),
        mode=InterviewMode(mode),
        allow_draft=allow_draft,
        signals=signals,
    )


@pytest.mark.parametrize("role", list(Role))
@pytest.mark.parametrize("level", list(Level))
@pytest.mark.parametrize("mode", list(InterviewMode))
def test_every_role_level_mode_has_a_valid_selection(role, level, mode) -> None:
    selection = _select(role, level, mode)
    catalog = LIBRARY.catalog
    mode_cfg = catalog.modes[mode]
    level_cfg = catalog.roles[role].levels[level]
    assert sum(s.target_questions for s in selection.skills) == mode_cfg.main_questions
    assert mode_cfg.skills.min <= len(selection.skills) <= mode_cfg.skills.max
    assert set(level_cfg.core_skills) <= {s.id for s in selection.skills}
    for selected in selection.skills:
        capacity = len(LIBRARY.skills[selected.id].seeds_for_level(level))
        assert 1 <= selected.target_questions <= capacity
    assert {ref.id for ref in selection.cross_cutting} == {"communication", "problem_solving"}


def test_without_documents_demo_uses_core_skills_only() -> None:
    selection = _select("ai_engineer", "fresher", "demo")
    assert [s.id for s in selection.skills] == ["rag_systems", "machine_learning"]
    assert all(s.is_core for s in selection.skills)


def test_jd_keywords_add_and_explain_an_optional_skill() -> None:
    signals = DocumentSignals(jd_text="Yêu cầu: Redis cache, Kafka, PostgreSQL")
    selection = _select("backend_developer", "fresher", "demo", signals)
    ids = [s.id for s in selection.skills]
    assert {"databases", "api_design", "system_design"} == set(ids)
    system_design = next(s for s in selection.skills if s.id == "system_design")
    assert any("JD nhắc tới" in reason for reason in system_design.reasons)


def test_draft_content_is_refused_without_permission() -> None:
    with pytest.raises(SelectionError):
        _select("ai_engineer", "fresher", "demo", allow_draft=False)


def test_keyword_matching_respects_word_boundaries() -> None:
    assert keyword_hits("Dùng SQL và Spark", ["sql", "spark", "park"]) == ["sql", "spark"]
    assert keyword_hits("nosql database", ["sql"]) == []


def test_allocation_respects_capacity_and_minimum() -> None:
    assert allocate_questions([0.4, 0.3, 0.3], [2, 5, 5], 6) == [2, 2, 2]
    assert allocate_questions([0.9, 0.1], [2, 5], 4) == [2, 2]
    with pytest.raises(SelectionError):
        allocate_questions([0.5, 0.5], [1, 1], 3)


def test_out_of_scope_requirements_depend_on_the_role_level_skills() -> None:
    requirements = ["RAG", "Kubernetes", "Figma"]
    ai_fresher = list(LIBRARY.catalog.roles[Role.AI_ENGINEER].levels[Level.FRESHER].skills)
    backend_junior = list(LIBRARY.catalog.roles[Role.BACKEND_DEVELOPER].levels[Level.JUNIOR].skills)
    assert unmatched_requirements(LIBRARY, requirements, ai_fresher) == ["Kubernetes", "Figma"]
    assert unmatched_requirements(LIBRARY, requirements, backend_junior) == ["RAG", "Figma"]
    # Generic phrasing used in real JDs is still recognised as in scope.
    jd_terms = ["LLM", "AI agent", "FastAPI"]
    assert unmatched_requirements(LIBRARY, jd_terms, ai_fresher) == ["FastAPI"]
