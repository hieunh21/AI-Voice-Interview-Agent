"""Evidence-based evaluation with a fake LLM that reads the real prompts."""

import asyncio

import pytest
from helpers import default_cross_cutting, default_thread_evaluation, fake_llm
from test_live_rules import PLAN

from ai.evaluation.evaluator import AnsweredTurn, EvaluationError, Evaluator
from ai.evaluation.evidence import quote_is_verbatim
from ai.llm.base import LLMError, LLMTimeout
from ai.llm.fake import FakeLLM
from ai.prompts.evaluator import (
    CrossCuttingOut,
    ReportSummaryOut,
    ThreadEvaluationOut,
)
from ai.schemas.enums import EvaluationStatus, TurnKind
from ai.scoring import weighted_score

LONG = (
    "RAG truy xuất các đoạn tài liệu liên quan rồi đưa vào ngữ cảnh để mô hình trả lời, "
    "đo bằng Recall@K."
)


def _turns() -> list[AnsweredTurn]:
    q1, q2 = PLAN.questions[0], PLAN.questions[1]
    return [
        AnsweredTurn(
            1, "q_001", None, TurnKind.MAIN, q1.question_text, "Dùng vector database.", False
        ),
        AnsweredTurn(
            2, "q_001.f1", "q_001", TurnKind.FOLLOW_UP, "Bạn giải thích thêm?", LONG, True
        ),
        AnsweredTurn(3, "q_002", None, TurnKind.MAIN, q2.question_text, "Em không biết ạ.", False),
    ]


def _evaluate(llm, turns=None):
    evaluator = Evaluator(llm)
    turns = _turns() if turns is None else turns
    return asyncio.run(evaluator.evaluate(session_id="s1", plan=PLAN, turns=turns))


def test_quote_verification() -> None:
    answer = "Em dùng “hybrid search” với BM25,   rồi đo Recall@K."
    assert quote_is_verbatim('dùng "hybrid search" với bm25', answer)
    assert quote_is_verbatim("rồi đo Recall@K.", answer)
    assert not quote_is_verbatim("dùng reranker", answer)
    assert not quote_is_verbatim("..", answer)


def test_valid_evaluation_produces_a_reproducible_report() -> None:
    llm = fake_llm()
    evaluation = _evaluate(llm)
    report = evaluation.report
    assert [r.question_id for r in report.questions] == ["q_001", "q_002"]
    first = report.questions[0]
    assert first.status is EvaluationStatus.SCORED
    assert first.turn_nos == [1, 2]  # the follow-up belongs to the thread
    question = PLAN.question("q_001")
    scores = {c.criterion_id: c.score for c in first.criteria}
    assert first.weighted_score == weighted_score(scores, question.rubric)
    assert [c.criterion_id for c in first.criteria] == [c.criterion_id for c in question.rubric]
    answers = {t.turn_no: t.answer_text for t in _turns()}
    for criterion in first.criteria:
        for evidence in criterion.evidence:
            assert quote_is_verbatim(evidence.quote, answers[evidence.turn_no])
    assert report.questions[1].weighted_score == 1.0  # "không biết" scores low, with evidence
    assert report.overall_score is not None
    assert {c.skill_id for c in report.cross_cutting} == {"communication", "problem_solving"}
    assert report.top_strengths == ["Giải thích rõ ràng"]
    assert report.versions.evaluator_model == "fake-llm"
    # The thread prompt carries frozen rubric anchors, expected points and turn-numbered answers.
    thread_prompt = next(p for p, s in llm.calls if s is ThreadEvaluationOut)
    assert question.expected_points[0] in thread_prompt
    assert PLAN.rubric_criteria["technical_accuracy"].anchors[5] in thread_prompt
    assert '<candidate_answer turn="2">' in thread_prompt


def test_invented_quotes_never_reach_the_report() -> None:
    report = _evaluate(fake_llm(evaluation_mode="invented")).report
    assert all(r.status is EvaluationStatus.INSUFFICIENT_EVIDENCE for r in report.questions)
    assert all(c.score is None and not c.evidence for r in report.questions for c in r.criteria)
    assert report.overall_score is None


def test_invalid_evidence_is_retried_once_with_feedback() -> None:
    llm = fake_llm(evaluation_mode="invented_once")
    report = _evaluate(llm).report
    assert all(r.status is EvaluationStatus.SCORED for r in report.questions)
    thread_calls = [p for p, s in llm.calls if s is ThreadEvaluationOut]
    assert len(thread_calls) == 4  # 2 threads × (first try + corrected retry)
    assert any("Lần chấm trước không hợp lệ" in p for p in thread_calls)


def test_model_can_flag_unusable_transcripts() -> None:
    report = _evaluate(fake_llm(evaluation_mode="insufficient")).report
    assert {r.status for r in report.questions} == {EvaluationStatus.INSUFFICIENT_EVIDENCE}


def test_unavailable_llm_fails_the_job_so_it_can_be_retried() -> None:
    with pytest.raises(LLMError):
        _evaluate(fake_llm(evaluation_error=LLMTimeout("slow")))


def test_nothing_to_evaluate() -> None:
    with pytest.raises(EvaluationError):
        _evaluate(fake_llm(), turns=[])
    with pytest.raises(EvaluationError):
        asyncio.run(Evaluator(None).evaluate(session_id="s", plan=PLAN, turns=_turns()))


def test_summary_and_cross_cutting_failures_are_not_fatal() -> None:
    def responder(system, prompt, schema):
        if schema is ThreadEvaluationOut:
            return default_thread_evaluation(prompt, "valid")
        if schema is CrossCuttingOut:
            return LLMTimeout("slow")
        if schema is ReportSummaryOut:
            return LLMTimeout("slow")
        raise AssertionError(schema)

    report = _evaluate(FakeLLM(responder=responder)).report
    assert report.cross_cutting == []
    assert report.top_strengths == ["Điểm mạnh giả lập"]  # deterministic fallback
    assert report.study_topics == ["ý còn thiếu"]


def test_cross_cutting_scores_need_verified_evidence() -> None:
    def responder(system, prompt, schema):
        if schema is ThreadEvaluationOut:
            return default_thread_evaluation(prompt, "valid")
        if schema is CrossCuttingOut:
            out = default_cross_cutting(prompt)
            bad = (
                out.skills[0]
                .criteria[0]
                .model_copy(
                    update={
                        "evidence": [
                            out.skills[0]
                            .criteria[0]
                            .evidence[0]
                            .model_copy(update={"quote": "câu không hề có trong transcript"})
                        ]
                    }
                )
            )
            out.skills[0].criteria[0] = bad
            return out
        return ReportSummaryOut(
            skill_summaries=[], top_strengths=[], priority_improvements=[], study_topics=[]
        )

    report = _evaluate(FakeLLM(responder=responder)).report
    first = report.cross_cutting[0].criteria[0]
    assert first.score is None
    assert first.evidence == []
