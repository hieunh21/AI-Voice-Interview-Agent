"""Backend-enforced interview rules (LIVE). Pure functions over the frozen plan and the turns.

The LLM proposes follow_up / clarify / move_on; these rules decide what actually happens:
- turns are reserved for every remaining main question, so follow-ups never cost skill coverage;
- at most `max_followups_per_question` follow-ups and one clarification per question thread;
- no extra turns when little time is left; the interview ends on plan completion, max turns or
  time budget. Only these rules can end an interview.
"""

import re
from dataclasses import dataclass

from ai.schemas.enums import EndReason, NextAction, TurnKind
from ai.schemas.interview import AnswerDecision, InterviewPlan

MAX_CLARIFY_PER_QUESTION = 1
MIN_SECONDS_FOR_EXTRA_TURN = 90
_WS = re.compile(r"\s+")


@dataclass(frozen=True)
class TurnRecord:
    turn_no: int
    question_id: str
    parent_question_id: str | None
    kind: TurnKind
    skill_id: str
    question_text: str
    answer_text: str | None

    @property
    def thread(self) -> str:
        return self.parent_question_id or self.question_id


@dataclass(frozen=True)
class Budget:
    mains_total: int
    mains_asked: int
    turns_used: int
    max_turns: int
    followups_in_thread: int
    clarifies_in_thread: int
    max_followups: int
    seconds_left: float

    @property
    def spare_turns(self) -> int:
        """Turns available beyond those reserved for the remaining main questions."""
        return (self.max_turns - self.turns_used) - (self.mains_total - self.mains_asked)

    @property
    def followups_left(self) -> int:
        return max(0, self.max_followups - self.followups_in_thread)


@dataclass(frozen=True)
class NextTurn:
    question_id: str
    parent_question_id: str | None
    kind: TurnKind
    skill_id: str
    question_text: str


@dataclass(frozen=True)
class Outcome:
    """What the backend will do after an answer: ask `next_turn`, or end with `end_reason`."""

    action: str  # "follow_up" | "clarify" | "next_main" | "finish"
    next_turn: NextTurn | None
    end_reason: EndReason | None
    overridden: bool  # the backend changed the model's proposed action


def budget(plan: InterviewPlan, turns: list[TurnRecord], elapsed_seconds: float) -> Budget:
    current = turns[-1]
    thread = [t for t in turns if t.thread == current.thread]
    return Budget(
        mains_total=len(plan.questions),
        mains_asked=sum(t.kind is TurnKind.MAIN for t in turns),
        turns_used=len(turns),
        max_turns=plan.limits.max_turns,
        followups_in_thread=sum(t.kind is TurnKind.FOLLOW_UP for t in thread),
        clarifies_in_thread=sum(t.kind is TurnKind.CLARIFY for t in thread),
        max_followups=plan.limits.max_followups_per_question,
        seconds_left=plan.limits.time_budget_minutes * 60 - elapsed_seconds,
    )


def allowed_actions(b: Budget) -> set[NextAction]:
    allowed = {NextAction.MOVE_ON}
    if b.spare_turns >= 1 and b.seconds_left >= MIN_SECONDS_FOR_EXTRA_TURN:
        if b.followups_left > 0:
            allowed.add(NextAction.FOLLOW_UP)
        if b.clarifies_in_thread < MAX_CLARIFY_PER_QUESTION:
            allowed.add(NextAction.CLARIFY)
    return allowed


def _normalise(text: str) -> str:
    return _WS.sub(" ", text).strip().casefold()


def resolve(
    plan: InterviewPlan,
    turns: list[TurnRecord],
    decision: AnswerDecision,
    elapsed_seconds: float,
) -> Outcome:
    """Turn a (validated) decision into the next turn, enforcing every limit."""
    b = budget(plan, turns, elapsed_seconds)
    current = turns[-1]

    plan_done = b.mains_asked >= b.mains_total
    if b.seconds_left <= 0:
        return Outcome("finish", None, EndReason.TIME_BUDGET, overridden=False)
    if b.turns_used >= b.max_turns:
        # With turns reserved for every main question, the last turn usually completes the plan.
        reason = EndReason.PLAN_COMPLETED if plan_done else EndReason.MAX_TURNS
        return Outcome("finish", None, reason, overridden=False)

    action = decision.next_action
    text = (decision.question_text or "").strip()
    asked = {_normalise(t.question_text) for t in turns}
    proposal_ok = (
        action in allowed_actions(b)
        and action is not NextAction.MOVE_ON
        and 5 <= len(text) <= 600
        and _normalise(text) not in asked
    )
    if proposal_ok:
        kind = TurnKind.FOLLOW_UP if action is NextAction.FOLLOW_UP else TurnKind.CLARIFY
        suffix = "f" if kind is TurnKind.FOLLOW_UP else "c"
        count = (b.followups_in_thread if kind is TurnKind.FOLLOW_UP else b.clarifies_in_thread) + 1
        return Outcome(
            action.value,
            NextTurn(
                question_id=f"{current.thread}.{suffix}{count}",
                parent_question_id=current.thread,
                kind=kind,
                skill_id=current.skill_id,
                question_text=text,
            ),
            None,
            overridden=False,
        )

    overridden = action is not NextAction.MOVE_ON
    if plan_done:
        return Outcome("finish", None, EndReason.PLAN_COMPLETED, overridden=overridden)
    following = plan.questions[b.mains_asked]
    return Outcome(
        "next_main",
        NextTurn(
            question_id=following.question_id,
            parent_question_id=None,
            kind=TurnKind.MAIN,
            skill_id=following.skill_id,
            question_text=following.question_text,
        ),
        None,
        overridden=overridden,
    )


def fallback_decision(
    plan: InterviewPlan, turns: list[TurnRecord], elapsed: float
) -> AnswerDecision:
    """Used when the LLM is unavailable: one playbook probe for short answers, otherwise move on."""
    b = budget(plan, turns, elapsed)
    current = turns[-1]
    question = plan.question(current.thread)
    asked = {_normalise(t.question_text) for t in turns}
    unused = [h for h in question.followup_hints if _normalise(h) not in asked]
    answer = (current.answer_text or "").strip()
    if (
        NextAction.FOLLOW_UP in allowed_actions(b)
        and b.followups_in_thread == 0
        and unused
        and len(answer) < 200
    ):
        return AnswerDecision(
            answer_quality="partial",
            next_action=NextAction.FOLLOW_UP,
            question_text=unused[0],
            brief_note="fallback: playbook probe",
        )
    return AnswerDecision(
        answer_quality="partial", next_action=NextAction.MOVE_ON, brief_note="fallback: move on"
    )


def first_turn(plan: InterviewPlan) -> NextTurn:
    first = plan.questions[0]
    return NextTurn(
        question_id=first.question_id,
        parent_question_id=None,
        kind=TurnKind.MAIN,
        skill_id=first.skill_id,
        question_text=first.question_text,
    )
