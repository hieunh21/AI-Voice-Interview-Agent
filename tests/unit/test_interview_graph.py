"""LIVE graph branches with a fake LLM (good / partial / don't know / repeat / failures)."""

import asyncio

from helpers import fake_llm
from test_live_rules import PLAN, turn

from ai.graphs.interview_graph import Interviewer
from ai.live_rules import TurnRecord
from ai.llm.base import LLMTimeout
from ai.llm.fake import FakeLLM
from ai.prompts.interviewer import LiveDecisionOut
from ai.schemas.enums import TurnKind


def _next(interviewer: Interviewer, turns: list[TurnRecord], elapsed: float = 60):
    return asyncio.run(interviewer.next_step(PLAN, turns, elapsed))


def _scripted(out: LiveDecisionOut) -> FakeLLM:
    return FakeLLM(responder=lambda system, prompt, schema: out)


def test_complete_answer_moves_to_the_next_planned_question() -> None:
    long_answer = "RAG truy xuất tài liệu liên quan rồi đưa vào ngữ cảnh để mô hình trả lời. " * 2
    result = _next(Interviewer(fake_llm()), [turn(1, "q_001", answer=long_answer)])
    assert result.source == "llm"
    assert result.outcome.action == "next_main"
    assert result.outcome.next_turn.question_id == "q_002"


def test_partial_answer_gets_a_follow_up_that_quotes_the_candidate() -> None:
    llm = fake_llm()
    result = _next(Interviewer(llm), [turn(1, "q_001", answer="Dùng vector database.")])
    assert result.outcome.action == "follow_up"
    assert "Dùng vector database" in result.outcome.next_turn.question_text
    prompt, _ = llm.calls[-1]
    assert "<candidate_answer>Dùng vector database.</candidate_answer>" in prompt
    assert "follow_up" in prompt.split("Hành động được phép:")[-1]
    # Expected points are given to the model for comparison only.
    assert PLAN.questions[0].expected_points[0] in prompt


def test_dont_know_moves_on_without_pressing() -> None:
    result = _next(Interviewer(fake_llm()), [turn(1, "q_001", answer="Em không biết ạ.")])
    assert result.decision.answer_quality.value == "no_answer"
    assert result.outcome.action == "next_main"


def test_candidate_asking_to_repeat_gets_a_clarification() -> None:
    out = LiveDecisionOut(
        answer_quality="no_answer",
        covered_points=[],
        missing_points=[],
        next_action="clarify",
        question_text="Mình hỏi lại: khi nào nên dùng RAG thay vì gọi thẳng LLM?",
        brief_note="xin nhắc lại",
    )
    result = _next(
        Interviewer(_scripted(out)), [turn(1, "q_001", answer="Anh nhắc lại được không?")]
    )
    assert result.outcome.next_turn.kind is TurnKind.CLARIFY


def test_llm_is_not_called_when_only_move_on_is_allowed() -> None:
    llm = fake_llm()
    turns = [turn(1, "q_001"), turn(2, "q_001.f1", TurnKind.FOLLOW_UP, answer="ngắn")]
    turns += [turn(3, "q_001.c1", TurnKind.CLARIFY, answer="ngắn")]
    result = _next(Interviewer(llm), turns)
    assert llm.calls == []
    assert result.source == "rules"
    assert result.outcome.next_turn.question_id == "q_002"


def test_llm_failure_falls_back_to_a_playbook_probe() -> None:
    result = _next(
        Interviewer(fake_llm(live_error=LLMTimeout("slow"))), [turn(1, "q_001", answer="ngắn")]
    )
    assert result.source == "fallback"
    assert result.outcome.next_turn.question_text == PLAN.questions[0].followup_hints[0]


def test_unusable_model_output_falls_back() -> None:
    out = LiveDecisionOut(
        answer_quality="partial",
        covered_points=[],
        missing_points=[],
        next_action="follow_up",
        question_text="",  # a follow-up without a question
        brief_note="",
    )
    result = _next(Interviewer(_scripted(out)), [turn(1, "q_001", answer="x" * 300)])
    assert result.source == "fallback"
    assert result.outcome.action == "next_main"


def test_no_llm_configured_still_runs_the_interview() -> None:
    result = _next(Interviewer(None), [turn(1, "q_001", answer="ngắn")])
    assert result.source == "fallback"
    assert result.outcome.action == "follow_up"
