"""PREP graph: optional documents → playbook selection → bounded context → plan → frozen snapshot.

    START → analyze_documents → select_playbooks → build_context
    build_context → propose_plan (LLM, retried once) → assemble_plan → END
    build_context / propose_plan → fallback_plan (seeds only) → assemble_plan

`propose_plan` asks the LLM (retried once on invalid output). Quota errors, timeouts or a
missing LLM route to `fallback_plan`, which builds the plan from reviewed seeds, so preparing an
interview never depends on the LLM being available.
"""

import logging
import random
from dataclasses import dataclass
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from ai.context_builder import DEFAULT_BUDGET_CHARS, PlannerContext, build_planner_context
from ai.llm.base import LLMError, LLMInvalidOutput, StructuredLLM
from ai.nodes.document_analysis import analyze_documents
from ai.nodes.planner import (
    DETERMINISTIC_MODEL,
    PlanInputs,
    assemble_plan,
    deterministic_drafts,
    propose_with_llm,
    validate_llm_drafts,
)
from ai.playbook_loader import PlaybookLibrary
from ai.playbook_selector import DocumentSignals, select_playbooks, unmatched_requirements
from ai.schemas.documents import DocumentAnalysis
from ai.schemas.interview import InterviewPlan, InterviewSetup, PlaybookSelection

logger = logging.getLogger(__name__)

MAX_LLM_ATTEMPTS = 2
FALLBACK_WARNING = (
    "Dịch vụ AI tạm thời không khả dụng nên kế hoạch được lập từ ngân hàng câu hỏi đã duyệt, "
    "chưa cá nhân hóa theo CV/JD."
)
MAX_OUT_OF_SCOPE = 3


class PrepState(TypedDict, total=False):
    setup: InterviewSetup
    session_key: str
    analysis: DocumentAnalysis
    selection: PlaybookSelection
    context: PlannerContext
    drafts: list
    planner_model: str
    attempts: int
    llm_failed: bool
    warnings: list[str]
    plan: InterviewPlan


@dataclass(frozen=True)
class PrepResult:
    plan: InterviewPlan
    analysis: DocumentAnalysis
    planner_model: str


class Preparer:
    def __init__(
        self,
        library: PlaybookLibrary,
        llm: StructuredLLM | None,
        *,
        allow_draft: bool,
        context_budget: int = DEFAULT_BUDGET_CHARS,
    ) -> None:
        self._library = library
        self._llm = llm
        self._allow_draft = allow_draft
        self._budget = context_budget
        self.graph = self._build()

    def _build(self):
        graph = StateGraph(PrepState)
        graph.add_node("analyze_documents", self._analyze)
        graph.add_node("select_playbooks", self._select)
        graph.add_node("build_context", self._context)
        graph.add_node("propose_plan", self._propose)
        graph.add_node("fallback_plan", self._fallback)
        graph.add_node("assemble_plan", self._assemble)
        graph.add_edge(START, "analyze_documents")
        graph.add_edge("analyze_documents", "select_playbooks")
        graph.add_edge("select_playbooks", "build_context")
        graph.add_conditional_edges("build_context", self._route_after_context)
        graph.add_conditional_edges("propose_plan", self._route_after_proposal)
        graph.add_edge("fallback_plan", "assemble_plan")
        graph.add_edge("assemble_plan", END)
        return graph.compile()

    async def run(self, setup: InterviewSetup, *, session_key: str) -> PrepResult:
        state = await self.graph.ainvoke(
            {"setup": setup, "session_key": session_key, "attempts": 0, "warnings": []}
        )
        return PrepResult(
            plan=state["plan"], analysis=state["analysis"], planner_model=state["planner_model"]
        )

    # ------------------------------------------------------------------ nodes

    async def _analyze(self, state: PrepState) -> PrepState:
        setup = state["setup"]
        analysis = await analyze_documents(
            self._llm,
            cv_text=setup.cv_text,
            jd_text=setup.jd_text,
            role=setup.role,
            level=setup.level,
        )
        warnings = [*state["warnings"], *analysis.warnings]
        # Extraction already failed in this request: do not wait for the LLM a second time.
        extraction_failed = self._llm is not None and analysis.source == "keywords"
        if analysis.job is not None and self._library.catalog is not None:
            role_level = self._library.catalog.roles[setup.role].levels[setup.level]
            out_of_scope = unmatched_requirements(
                self._library, analysis.job.required_skills, list(role_level.skills)
            )
            if out_of_scope:
                warnings.append(
                    f"JD yêu cầu {', '.join(out_of_scope[:MAX_OUT_OF_SCOPE])} — nằm ngoài phạm vi "
                    "kỹ năng được hỗ trợ nên sẽ không có câu hỏi riêng."
                )
        return {"analysis": analysis, "warnings": warnings, "llm_failed": extraction_failed}

    async def _select(self, state: PrepState) -> PrepState:
        setup, analysis = state["setup"], state["analysis"]
        cv_terms: tuple[str, ...] = ()
        if analysis.candidate is not None:
            cv_terms = tuple(analysis.candidate.skills) + tuple(
                tech for project in analysis.candidate.projects for tech in project.technologies
            )
        jd_terms: tuple[str, ...] = ()
        if analysis.job is not None:
            jd_terms = tuple(analysis.job.required_skills + analysis.job.nice_to_have)
        selection = select_playbooks(
            self._library,
            role=setup.role,
            level=setup.level,
            mode=setup.mode,
            allow_draft=self._allow_draft,
            signals=DocumentSignals(
                cv_text=setup.cv_text or "",
                jd_text=setup.jd_text or "",
                cv_terms=cv_terms,
                jd_terms=jd_terms,
            ),
        )
        return {"selection": selection}

    async def _context(self, state: PrepState) -> PrepState:
        context = build_planner_context(
            self._library, state["selection"], state["setup"].level, budget_chars=self._budget
        )
        if context.truncated:
            logger.info("Planner context trimmed: %d block(s) dropped", context.dropped_blocks)
        return {"context": context}

    async def _propose(self, state: PrepState) -> PrepState:
        assert self._llm is not None
        attempts = state["attempts"] + 1
        try:
            out = await propose_with_llm(self._llm, self._inputs(state), state["context"])
        except LLMInvalidOutput as exc:
            logger.warning("Planner attempt %d returned invalid output: %s", attempts, exc)
            return {"attempts": attempts, "llm_failed": attempts >= MAX_LLM_ATTEMPTS}
        except LLMError as exc:
            logger.warning("Planner LLM unavailable: %s", exc)
            return {"attempts": attempts, "llm_failed": True}
        drafts = validate_llm_drafts(out, self._inputs(state), self._rng(state))
        return {"attempts": attempts, "drafts": drafts, "planner_model": self._llm.model_id}

    async def _fallback(self, state: PrepState) -> PrepState:
        warnings = list(state["warnings"])
        setup = state["setup"]
        if state.get("llm_failed") and (setup.cv_text or setup.jd_text):
            warnings.append(FALLBACK_WARNING)
        return {
            "drafts": deterministic_drafts(self._inputs(state), self._rng(state)),
            "planner_model": DETERMINISTIC_MODEL,
            "warnings": warnings,
        }

    async def _assemble(self, state: PrepState) -> PrepState:
        plan = assemble_plan(
            state["drafts"],
            self._inputs(state),
            planner_model=state["planner_model"],
            warnings=state["warnings"],
        )
        return {"plan": plan}

    # ------------------------------------------------------------------ routing

    def _route_after_context(self, state: PrepState) -> Literal["propose_plan", "fallback_plan"]:
        if self._llm is None or state.get("llm_failed"):
            return "fallback_plan"
        return "propose_plan"

    def _route_after_proposal(
        self, state: PrepState
    ) -> Literal["assemble_plan", "propose_plan", "fallback_plan"]:
        if state.get("drafts"):
            return "assemble_plan"
        if state.get("llm_failed"):
            return "fallback_plan"
        return "propose_plan"

    # ------------------------------------------------------------------ helpers

    def _inputs(self, state: PrepState) -> PlanInputs:
        return PlanInputs(
            library=self._library,
            selection=state["selection"],
            setup=state["setup"],
            analysis=state["analysis"],
        )

    @staticmethod
    def _rng(state: PrepState) -> random.Random:
        return random.Random(state["session_key"])
