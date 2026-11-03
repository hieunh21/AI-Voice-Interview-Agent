"""LIVE graph: analyse the latest answer and decide the next turn, within backend-enforced rules.

    START ─┬→ analyze_answer (LLM) ─┬→ apply_rules → END
           │                        └→ fallback_decision ─┐
           ├→ fallback_decision (no LLM / LLM failed) ────┤
           └→ forced_move_on (only move_on is allowed) ───┴→ apply_rules

The graph is stateless per request: state is rebuilt from the database (frozen plan + turns),
so resuming after a refresh or restart needs no checkpointer.
"""

import logging
import time
from dataclasses import dataclass
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from ai.live_rules import (
    Outcome,
    TurnRecord,
    allowed_actions,
    budget,
    fallback_decision,
    resolve,
)
from ai.llm.base import LLMError, StructuredLLM
from ai.prompts import interviewer as prompt
from ai.schemas.enums import NextAction
from ai.schemas.interview import AnswerDecision, InterviewPlan

logger = logging.getLogger(__name__)

DecisionSource = Literal["llm", "fallback", "rules"]


class LiveState(TypedDict, total=False):
    plan: InterviewPlan
    turns: list[TurnRecord]
    elapsed: float
    decision: AnswerDecision
    source: DecisionSource
    outcome: Outcome


@dataclass(frozen=True)
class LiveResult:
    decision: AnswerDecision
    source: DecisionSource
    outcome: Outcome
    model_id: str
    latency_ms: int


def to_decision(out: prompt.LiveDecisionOut) -> AnswerDecision:
    """Convert raw model output to the validated contract (raises ValidationError if unusable)."""
    asks = out.next_action in ("follow_up", "clarify")
    return AnswerDecision(
        answer_quality=out.answer_quality,
        covered_points=[p.strip() for p in out.covered_points if p.strip()][:10],
        missing_points=[p.strip() for p in out.missing_points if p.strip()][:10],
        next_action=out.next_action,
        question_text=" ".join(out.question_text.split()) if asks else None,
        brief_note=" ".join(out.brief_note.split())[:300],
    )


class Interviewer:
    def __init__(self, llm: StructuredLLM | None) -> None:
        self._llm = llm
        self.graph = self._build()

    def _build(self):
        graph = StateGraph(LiveState)
        graph.add_node("analyze_answer", self._analyze)
        graph.add_node("fallback_decision", self._fallback)
        graph.add_node("forced_move_on", self._forced)
        graph.add_node("apply_rules", self._apply)
        graph.add_conditional_edges(START, self._route_start)
        graph.add_conditional_edges("analyze_answer", self._route_after_analysis)
        graph.add_edge("fallback_decision", "apply_rules")
        graph.add_edge("forced_move_on", "apply_rules")
        graph.add_edge("apply_rules", END)
        return graph.compile()

    async def next_step(
        self, plan: InterviewPlan, turns: list[TurnRecord], elapsed_seconds: float
    ) -> LiveResult:
        started = time.perf_counter()
        state = await self.graph.ainvoke({"plan": plan, "turns": turns, "elapsed": elapsed_seconds})
        source = state["source"]
        return LiveResult(
            decision=state["decision"],
            source=source,
            outcome=state["outcome"],
            model_id=self._llm.model_id if self._llm and source == "llm" else source,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )

    # ------------------------------------------------------------------ routing

    def _route_start(
        self, state: LiveState
    ) -> Literal["analyze_answer", "fallback_decision", "forced_move_on"]:
        b = budget(state["plan"], state["turns"], state["elapsed"])
        if allowed_actions(b) == {NextAction.MOVE_ON}:
            return "forced_move_on"
        return "analyze_answer" if self._llm is not None else "fallback_decision"

    @staticmethod
    def _route_after_analysis(state: LiveState) -> Literal["apply_rules", "fallback_decision"]:
        return "apply_rules" if "decision" in state else "fallback_decision"

    # ------------------------------------------------------------------ nodes

    async def _analyze(self, state: LiveState) -> LiveState:
        assert self._llm is not None
        plan, turns = state["plan"], state["turns"]
        current = turns[-1]
        b = budget(plan, turns, state["elapsed"])
        thread = [(t.question_text, t.answer_text) for t in turns if t.thread == current.thread]
        try:
            out = await self._llm.generate(
                system=prompt.SYSTEM,
                prompt=prompt.build_prompt(
                    question=plan.question(current.thread),
                    thread=thread,
                    allowed=allowed_actions(b),
                    followups_left=b.followups_left,
                ),
                schema=prompt.LiveDecisionOut,
                temperature=0.3,
            )
            return {"decision": to_decision(out), "source": "llm"}
        except (LLMError, ValidationError) as exc:
            logger.warning("Answer analysis unavailable, using fallback: %s", type(exc).__name__)
            return {}

    async def _fallback(self, state: LiveState) -> LiveState:
        decision = fallback_decision(state["plan"], state["turns"], state["elapsed"])
        return {"decision": decision, "source": "fallback"}

    async def _forced(self, state: LiveState) -> LiveState:
        decision = AnswerDecision(
            answer_quality="partial",
            next_action=NextAction.MOVE_ON,
            brief_note="rules: no extra turns allowed",
        )
        return {"decision": decision, "source": "rules"}

    async def _apply(self, state: LiveState) -> LiveState:
        outcome = resolve(state["plan"], state["turns"], state["decision"], state["elapsed"])
        if outcome.overridden:
            logger.info(
                "Rules overrode %s → %s", state["decision"].next_action.value, outcome.action
            )
        return {"outcome": outcome}
