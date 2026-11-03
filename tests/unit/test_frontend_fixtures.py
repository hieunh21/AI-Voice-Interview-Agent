"""Contract test: the frontend mock fixtures must be valid backend responses.

Catches drift between frontend/src/api/types.ts and the Pydantic contracts, and checks the
invariants the real backend will guarantee (verbatim evidence, reproducible scores).
"""

from pathlib import Path

import pytest

from ai.playbook_loader import load_library
from ai.schemas.common import ContractModel
from ai.schemas.enums import EvaluationStatus, ReportStatus, SessionStatus
from ai.schemas.evaluation import InterviewReport
from ai.schemas.playbook import RubricCriterion
from ai.scoring import overall_score, skill_score, weighted_score
from app.schemas.interview import SessionView

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "frontend" / "src" / "mocks" / "fixtures"
FIXTURES = sorted(FIXTURE_DIR.glob("*.json"))

# The fixtures use the standard technical rubric weights (as in rag_systems.md).
STANDARD_RUBRIC = [
    RubricCriterion(criterion_id="technical_accuracy", weight=0.40),
    RubricCriterion(criterion_id="completeness", weight=0.25),
    RubricCriterion(criterion_id="reasoning", weight=0.20),
    RubricCriterion(criterion_id="practical_examples", weight=0.15),
]


class MockFixture(ContractModel):
    session: SessionView
    report: InterviewReport | None


def _load(path: Path) -> MockFixture:
    return MockFixture.model_validate_json(path.read_text(encoding="utf-8"))


def test_fixtures_cover_all_four_document_combinations() -> None:
    combos = {(f.session.has_cv, f.session.has_jd) for f in map(_load, FIXTURES)}
    assert combos == {(False, False), (True, False), (False, True), (True, True)}


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_fixture_session_invariants(path: Path) -> None:
    fixture = _load(path)
    session = fixture.session
    assert (fixture.report is not None) == (session.report_status is ReportStatus.COMPLETED)

    if session.status is SessionStatus.READY:
        assert session.turns == []
        assert session.started_at is None
    if session.status is SessionStatus.IN_PROGRESS:
        assert session.started_at is not None
        assert session.ended_at is None
    if session.status is SessionStatus.COMPLETED:
        assert session.ended_at is not None
        assert session.end_reason is not None

    preview = session.plan_preview
    assert preview is not None
    assert sum(s.target_questions for s in preview.skills) == preview.main_questions
    assert ("cv" in preview.input_sources) == session.has_cv
    assert ("jd" in preview.input_sources) == session.has_jd
    main_turns = [t for t in session.turns if t.kind.value == "main"]
    assert len(main_turns) <= preview.main_questions
    assert len(session.turns) <= preview.max_turns


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_fixture_report_evidence_and_scores(path: Path) -> None:
    fixture = _load(path)
    report, session = fixture.report, fixture.session
    if report is None:
        pytest.skip("no report in this fixture")

    assert report.session_id == str(session.id)
    assert (report.role, report.level, report.mode) == (session.role, session.level, session.mode)

    answers = {t.turn_no: t.answer_text or "" for t in session.turns}
    threads: dict[str, list[int]] = {}
    for turn in session.turns:
        root = turn.parent_question_id or turn.question_id
        threads.setdefault(root, []).append(turn.turn_no)

    criteria = [c for q in report.questions for c in q.criteria] + [
        c for cc in report.cross_cutting for c in cc.criteria
    ]
    for criterion in criteria:
        for evidence in criterion.evidence:
            assert evidence.quote in answers[evidence.turn_no], evidence.quote

    by_question = {}
    for result in report.questions:
        assert result.turn_nos == threads[result.question_id]
        if result.status is EvaluationStatus.SCORED:
            scores = {c.criterion_id: c.score for c in result.criteria}
            assert weighted_score(scores, STANDARD_RUBRIC) == result.weighted_score  # type: ignore[arg-type]
        by_question[result.question_id] = result.weighted_score

    for skill in report.skill_scores:
        assert skill.score == skill_score(by_question[q] for q in skill.question_ids)

    catalog = load_library().catalog
    assert catalog is not None
    level_cfg = catalog.roles[session.role].levels[session.level]
    weights = {skill_id: cfg.weight for skill_id, cfg in level_cfg.skills.items()}
    skill_scores = {s.skill_id: s.score for s in report.skill_scores}
    assert report.overall_score == overall_score(skill_scores, weights)
