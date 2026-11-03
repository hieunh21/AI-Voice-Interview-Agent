import asyncio

import pytest

from ai.graphs.prep_graph import Preparer
from ai.live_rules import (
    TurnRecord,
    allowed_actions,
    budget,
    fallback_decision,
    first_turn,
    resolve,
)
from ai.playbook_loader import load_library
from ai.schemas.enums import EndReason, NextAction, TurnKind
from ai.schemas.interview import AnswerDecision, InterviewPlan, InterviewSetup

LIBRARY = load_library()


def make_plan(mode: str = "demo") -> InterviewPlan:
    setup = InterviewSetup(role="ai_engineer", level="fresher", mode=mode)
    preparer = Preparer(LIBRARY, None, allow_draft=True)
    return asyncio.run(preparer.run(setup, session_key="live-tests")).plan


PLAN = make_plan()  # demo: 3 main questions, 1 follow-up each, 6 turns, 12 minutes


def turn(no, qid, kind=TurnKind.MAIN, answer="Một câu trả lời.", text=None):
    parent = None if kind is TurnKind.MAIN else qid.split(".")[0]
    skill = PLAN.question(qid.split(".")[0]).skill_id
    return TurnRecord(no, qid, parent, kind, skill, text or f"Câu hỏi {qid}?", answer)


def decide(action, text=None):
    return AnswerDecision(answer_quality="partial", next_action=action, question_text=text)


def test_first_turn_is_the_first_planned_question() -> None:
    first = first_turn(PLAN)
    assert (first.question_id, first.kind) == ("q_001", TurnKind.MAIN)
    assert first.question_text == PLAN.questions[0].question_text


def test_follow_up_and_clarify_allowed_with_spare_turns() -> None:
    b = budget(PLAN, [turn(1, "q_001")], elapsed_seconds=60)
    assert b.spare_turns == 3
    assert allowed_actions(b) == {NextAction.MOVE_ON, NextAction.FOLLOW_UP, NextAction.CLARIFY}


def test_follow_up_limit_per_question() -> None:
    turns = [turn(1, "q_001"), turn(2, "q_001.f1", TurnKind.FOLLOW_UP)]
    assert NextAction.FOLLOW_UP not in allowed_actions(budget(PLAN, turns, 60))


def test_turns_are_reserved_for_remaining_main_questions() -> None:
    turns = [
        turn(1, "q_001"),
        turn(2, "q_001.f1", TurnKind.FOLLOW_UP),
        turn(3, "q_001.c1", TurnKind.CLARIFY),
        turn(4, "q_002"),
        turn(5, "q_002.c1", TurnKind.CLARIFY),
    ]
    b = budget(PLAN, turns, 60)
    assert b.spare_turns == 0
    assert allowed_actions(b) == {NextAction.MOVE_ON}
    outcome = resolve(PLAN, turns, decide(NextAction.FOLLOW_UP, "Bạn giải thích thêm?"), 60)
    assert outcome.action == "next_main"
    assert outcome.next_turn.question_id == "q_003"
    assert outcome.overridden


def test_little_time_left_forbids_extra_turns() -> None:
    elapsed = PLAN.limits.time_budget_minutes * 60 - 30
    assert allowed_actions(budget(PLAN, [turn(1, "q_001")], elapsed)) == {NextAction.MOVE_ON}


def test_valid_follow_up_creates_a_thread_turn() -> None:
    outcome = resolve(
        PLAN, [turn(1, "q_001")], decide(NextAction.FOLLOW_UP, "Vì sao bạn chọn BM25?"), 60
    )
    nxt = outcome.next_turn
    assert outcome.action == "follow_up"
    assert (nxt.question_id, nxt.parent_question_id, nxt.kind) == (
        "q_001.f1",
        "q_001",
        TurnKind.FOLLOW_UP,
    )
    assert nxt.skill_id == PLAN.questions[0].skill_id


def test_clarification_gets_its_own_id() -> None:
    outcome = resolve(PLAN, [turn(1, "q_001")], decide(NextAction.CLARIFY, "Ý bạn là gì?"), 60)
    assert outcome.next_turn.question_id == "q_001.c1"
    assert outcome.next_turn.kind is TurnKind.CLARIFY


def test_repeated_question_is_replaced_by_the_next_main_question() -> None:
    turns = [turn(1, "q_001", text="RAG là gì?")]
    outcome = resolve(PLAN, turns, decide(NextAction.FOLLOW_UP, "  rag là   gì? "), 60)
    assert outcome.action == "next_main"


def test_move_on_after_the_last_question_completes_the_plan() -> None:
    turns = [turn(1, "q_001"), turn(2, "q_002"), turn(3, "q_003")]
    outcome = resolve(PLAN, turns, decide(NextAction.MOVE_ON), 60)
    assert (outcome.action, outcome.end_reason) == ("finish", EndReason.PLAN_COMPLETED)


@pytest.mark.parametrize(
    ("turns", "elapsed", "reason"),
    [
        ([turn(1, "q_001")], 12 * 60 + 1, EndReason.TIME_BUDGET),
        (
            # Last allowed turn answered and every main question asked: the plan is complete.
            [
                turn(1, "q_001"),
                turn(2, "q_001.f1", TurnKind.FOLLOW_UP),
                turn(3, "q_002"),
                turn(4, "q_002.f1", TurnKind.FOLLOW_UP),
                turn(5, "q_003"),
                turn(6, "q_003.f1", TurnKind.FOLLOW_UP),
            ],
            60,
            EndReason.PLAN_COMPLETED,
        ),
        (
            # Safety net: turns exhausted with main questions left (cannot happen via the API).
            [
                turn(1, "q_001"),
                turn(2, "q_001.f1", TurnKind.FOLLOW_UP),
                turn(3, "q_001.c1", TurnKind.CLARIFY),
                turn(4, "q_002"),
                turn(5, "q_002.f1", TurnKind.FOLLOW_UP),
                turn(6, "q_002.c1", TurnKind.CLARIFY),
            ],
            60,
            EndReason.MAX_TURNS,
        ),
    ],
)
def test_hard_limits_end_the_interview(turns, elapsed, reason) -> None:
    outcome = resolve(PLAN, turns, decide(NextAction.FOLLOW_UP, "Câu mới?"), elapsed)
    assert (outcome.action, outcome.end_reason) == ("finish", reason)


def test_fallback_uses_a_playbook_probe_for_short_answers_once() -> None:
    short = [turn(1, "q_001", answer="Không rõ lắm.")]
    decision = fallback_decision(PLAN, short, 60)
    assert decision.next_action is NextAction.FOLLOW_UP
    assert decision.question_text == PLAN.questions[0].followup_hints[0]

    long_answer = [turn(1, "q_001", answer="x" * 300)]
    assert fallback_decision(PLAN, long_answer, 60).next_action is NextAction.MOVE_ON
