"""Session evaluator: one LLM call per question thread, one for cross-cutting skills, one summary.

The LLM scores; this module verifies and computes:
- every score must cite a verbatim quote from the cited turn (checked, invalid quotes dropped);
- a thread whose scores cannot be backed by evidence is re-asked once with the problems listed,
  then marked `insufficient_evidence` — an unbacked score never reaches the report;
- weighted, skill and overall scores are computed deterministically from the frozen rubric and
  frozen skill weights (`ai.scoring`).
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from ai.evaluation.evidence import quote_is_verbatim
from ai.llm.base import LLMError, LLMInvalidOutput, StructuredLLM
from ai.prompts import evaluator as prompts
from ai.schemas.enums import EvaluationStatus, TurnKind
from ai.schemas.evaluation import (
    CriterionScore,
    CrossCuttingResult,
    EvaluationResult,
    EvidenceQuote,
    InterviewReport,
    ReportVersions,
    SkillScore,
)
from ai.schemas.interview import InterviewPlan, PlannedQuestion
from ai.schemas.playbook import RubricCriterion
from ai.scoring import overall_score, skill_score, weighted_score

logger = logging.getLogger(__name__)

MAX_EVIDENCE = 3
MAX_LIST_ITEMS = 5
INSUFFICIENT = "Không đủ bằng chứng trong transcript để chấm tiêu chí này."


class EvaluationError(Exception):
    """The session cannot be evaluated now (no answers, or the LLM is unavailable)."""


@dataclass(frozen=True)
class AnsweredTurn:
    turn_no: int
    question_id: str
    parent_question_id: str | None
    kind: TurnKind
    question_text: str
    answer_text: str
    from_voice: bool

    @property
    def thread(self) -> str:
        return self.parent_question_id or self.question_id

    def as_prompt_tuple(self) -> tuple[int, str, str, bool]:
        return (self.turn_no, self.question_text, self.answer_text, self.from_voice)


@dataclass(frozen=True)
class SessionEvaluation:
    report: InterviewReport
    results: list[EvaluationResult]


def _items(values: list[str], limit: int = MAX_LIST_ITEMS) -> list[str]:
    return [v.strip() for v in values if v and v.strip()][:limit]


def _verified(criterion: prompts.CriterionOut, answers: dict[int, str]) -> list[EvidenceQuote]:
    evidence = []
    for item in criterion.evidence:
        answer = answers.get(item.turn_no)
        if answer is not None and quote_is_verbatim(item.quote, answer):
            evidence.append(EvidenceQuote(turn_no=item.turn_no, quote=item.quote.strip()[:500]))
    return evidence[:MAX_EVIDENCE]


class Evaluator:
    def __init__(self, llm: StructuredLLM | None, *, concurrency: int = 3, attempts: int = 2):
        self._llm = llm
        self._semaphore = asyncio.Semaphore(concurrency)
        self._attempts = attempts

    @property
    def model_id(self) -> str | None:
        return self._llm.model_id if self._llm else None

    async def evaluate(
        self, *, session_id: str, plan: InterviewPlan, turns: list[AnsweredTurn]
    ) -> SessionEvaluation:
        if self._llm is None:
            raise EvaluationError("no LLM configured for evaluation")
        threads: dict[str, list[AnsweredTurn]] = {}
        for turn in sorted(turns, key=lambda t: t.turn_no):
            threads.setdefault(turn.thread, []).append(turn)
        if not threads:
            raise EvaluationError("no answered turns to evaluate")

        ordered = [q for q in plan.questions if q.question_id in threads]
        results = await asyncio.gather(
            *(self._thread(plan, q, threads[q.question_id]) for q in ordered)
        )
        cross = await self._cross_cutting(plan, turns)

        skill_scores = []
        for skill in plan.selected_skills:
            mine = [r for r in results if r.skill_id == skill.id]
            if mine:
                skill_scores.append(
                    SkillScore(
                        skill_id=skill.id,
                        skill_version=skill.version,
                        score=skill_score(r.weighted_score for r in mine),
                        question_ids=[r.question_id for r in mine],
                    )
                )
        weights = {s.id: s.weight or 1.0 for s in plan.selected_skills}
        overall = overall_score({s.skill_id: s.score for s in skill_scores}, weights)
        summary = await self._summary(plan, results, skill_scores, cross)
        skill_scores = [
            s.model_copy(update={"summary": summary["skills"].get(s.skill_id, "")})
            for s in skill_scores
        ]
        report = InterviewReport(
            session_id=session_id,
            role=plan.role,
            level=plan.level,
            mode=plan.mode,
            overall_score=overall,
            skill_scores=skill_scores,
            cross_cutting=cross,
            questions=results,
            top_strengths=summary["strengths"],
            priority_improvements=summary["improvements"],
            study_topics=summary["topics"],
            versions=ReportVersions(
                rubric=plan.versions.rubric,
                evaluator_prompt=prompts.EVALUATOR_PROMPT_VERSION,
                evaluator_model=self.model_id,
            ),
            generated_at=datetime.now(UTC),
        )
        return SessionEvaluation(report=report, results=list(results))

    # ------------------------------------------------------------------ question threads

    async def _thread(
        self, plan: InterviewPlan, question: PlannedQuestion, turns: list[AnsweredTurn]
    ) -> EvaluationResult:
        assert self._llm is not None
        prompt = prompts.build_thread_prompt(
            question=question,
            definitions=plan.rubric_criteria,
            turns=[t.as_prompt_tuple() for t in turns],
            level=plan.level.value,
        )
        problems = "kết quả không hợp lệ"
        for attempt in range(1, self._attempts + 1):
            async with self._semaphore:
                try:
                    out = await self._llm.generate(
                        system=prompts.THREAD_SYSTEM,
                        prompt=prompt,
                        schema=prompts.ThreadEvaluationOut,
                        temperature=0.0,
                    )
                except LLMInvalidOutput:
                    logger.warning(
                        "%s: invalid evaluation output (attempt %d)", question.question_id, attempt
                    )
                    continue
            result, problems = self._to_result(plan, question, out, turns)
            if result is not None:
                return result
            logger.warning(
                "%s: evidence check failed (attempt %d): %s",
                question.question_id,
                attempt,
                problems,
            )
            prompt += (
                f"\n\nLần chấm trước không hợp lệ: {problems}. Chấm lại: mỗi tiêu chí có điểm 1–5 "
                "phải có trích dẫn sao chép NGUYÊN VĂN từ câu trả lời của ứng viên ở đúng lượt."
            )
        return self._insufficient(plan, question, turns, problems)

    def _to_result(
        self,
        plan: InterviewPlan,
        question: PlannedQuestion,
        out: prompts.ThreadEvaluationOut,
        turns: list[AnsweredTurn],
    ) -> tuple[EvaluationResult | None, str]:
        if out.insufficient_evidence:
            return self._insufficient(plan, question, turns, "", out), ""
        answers = {t.turn_no: t.answer_text for t in turns}
        by_id = {c.criterion_id: c for c in out.criteria}
        criteria, problems = [], []
        for weighted in question.rubric:
            raw = by_id.get(weighted.criterion_id)
            if raw is None:
                problems.append(f"thiếu tiêu chí {weighted.criterion_id}")
                continue
            evidence = _verified(raw, answers)
            if not 1 <= raw.score <= 5 or not evidence:
                problems.append(f"{weighted.criterion_id}: thiếu điểm hoặc trích dẫn không khớp")
                continue
            criteria.append(
                CriterionScore(
                    criterion_id=weighted.criterion_id,
                    score=raw.score,
                    rationale=raw.rationale.strip() or "—",
                    evidence=evidence,
                )
            )
        if problems:
            return None, "; ".join(problems)
        scores = {c.criterion_id: c.score for c in criteria if c.score is not None}
        return (
            EvaluationResult(
                question_id=question.question_id,
                skill_id=question.skill_id,
                skill_version=self._skill_version(plan, question.skill_id),
                status=EvaluationStatus.SCORED,
                turn_nos=[t.turn_no for t in turns],
                criteria=criteria,
                weighted_score=weighted_score(scores, question.rubric),
                covered_points=_items(out.covered_points, 10),
                missed_points=_items(out.missed_points, 10),
                strengths=_items(out.strengths),
                gaps=_items(out.gaps),
                improvement_suggestion=out.improvement_suggestion.strip(),
            ),
            "",
        )

    def _insufficient(
        self,
        plan: InterviewPlan,
        question: PlannedQuestion,
        turns: list[AnsweredTurn],
        problems: str,
        out: prompts.ThreadEvaluationOut | None = None,
    ) -> EvaluationResult:
        suggestion = (out.improvement_suggestion.strip() if out else "") or (
            "Transcript của câu này không đủ để chấm. Hãy kiểm tra và sửa transcript "
            "trước khi gửi, "
            "và trả lời đầy đủ hơn."
        )
        if problems:
            logger.warning("%s marked insufficient_evidence: %s", question.question_id, problems)
        return EvaluationResult(
            question_id=question.question_id,
            skill_id=question.skill_id,
            skill_version=self._skill_version(plan, question.skill_id),
            status=EvaluationStatus.INSUFFICIENT_EVIDENCE,
            turn_nos=[t.turn_no for t in turns],
            criteria=[
                CriterionScore(criterion_id=c.criterion_id, rationale=INSUFFICIENT)
                for c in question.rubric
            ],
            improvement_suggestion=suggestion,
        )

    @staticmethod
    def _skill_version(plan: InterviewPlan, skill_id: str) -> str:
        return next(s.version for s in plan.selected_skills if s.id == skill_id)

    # ------------------------------------------------------------------ cross-cutting

    async def _cross_cutting(
        self, plan: InterviewPlan, turns: list[AnsweredTurn]
    ) -> list[CrossCuttingResult]:
        assert self._llm is not None
        if not plan.cross_cutting_skills:
            return []
        try:
            out = await self._llm.generate(
                system=prompts.CROSS_SYSTEM,
                prompt=prompts.build_cross_prompt(
                    skills=[(s.id, s.title, s.rubric) for s in plan.cross_cutting_skills],
                    definitions=plan.rubric_criteria,
                    turns=[t.as_prompt_tuple() for t in sorted(turns, key=lambda t: t.turn_no)],
                    level=plan.level.value,
                ),
                schema=prompts.CrossCuttingOut,
                temperature=0.0,
            )
        except LLMError as exc:
            logger.warning("Cross-cutting evaluation skipped: %s", exc)
            return []
        answers = {t.turn_no: t.answer_text for t in turns}
        by_skill = {s.skill_id: s for s in out.skills}
        results = []
        for skill in plan.cross_cutting_skills:
            raw = by_skill.get(skill.id)
            raw_criteria = {c.criterion_id: c for c in raw.criteria} if raw else {}
            criteria = [
                self._cross_criterion(c, raw_criteria.get(c.criterion_id), answers)
                for c in skill.rubric
            ]
            results.append(
                CrossCuttingResult(
                    skill_id=skill.id,
                    skill_version=skill.version,
                    criteria=criteria,
                    summary=(raw.summary.strip() if raw else ""),
                )
            )
        return results

    @staticmethod
    def _cross_criterion(
        weighted: RubricCriterion, raw: prompts.CriterionOut | None, answers: dict[int, str]
    ) -> CriterionScore:
        if raw is None or not 1 <= raw.score <= 5:
            rationale = (raw.rationale.strip() if raw else "") or INSUFFICIENT
            return CriterionScore(criterion_id=weighted.criterion_id, rationale=rationale)
        evidence = _verified(raw, answers)
        if not evidence:
            return CriterionScore(criterion_id=weighted.criterion_id, rationale=INSUFFICIENT)
        return CriterionScore(
            criterion_id=weighted.criterion_id,
            score=raw.score,
            rationale=raw.rationale.strip() or "—",
            evidence=evidence,
        )

    # ------------------------------------------------------------------ summary

    async def _summary(
        self,
        plan: InterviewPlan,
        results: list[EvaluationResult],
        skill_scores: list[SkillScore],
        cross: list[CrossCuttingResult],
    ) -> dict:
        assert self._llm is not None
        titles = {s.id: s.title for s in plan.selected_skills}
        facts = {
            "skills": [
                {"skill_id": s.skill_id, "title": titles.get(s.skill_id), "score": s.score}
                for s in skill_scores
            ],
            "questions": [
                {
                    "skill_id": r.skill_id,
                    "score": r.weighted_score,
                    "strengths": r.strengths,
                    "gaps": r.gaps,
                    "missed_points": r.missed_points,
                }
                for r in results
            ],
            "cross_cutting": [{"skill_id": c.skill_id, "summary": c.summary} for c in cross],
        }
        try:
            out = await self._llm.generate(
                system=prompts.SUMMARY_SYSTEM,
                prompt="Kết quả chấm (JSON):\n" + json.dumps(facts, ensure_ascii=False),
                schema=prompts.ReportSummaryOut,
                temperature=0.2,
            )
            return {
                "skills": {s.skill_id: s.summary.strip() for s in out.skill_summaries},
                "strengths": _items(out.top_strengths, 3),
                "improvements": _items(out.priority_improvements, 3),
                "topics": _items(out.study_topics, 5),
            }
        except LLMError as exc:
            logger.warning("Summary generation failed, using deterministic summary: %s", exc)
            return self._fallback_summary(results)

    @staticmethod
    def _fallback_summary(results: list[EvaluationResult]) -> dict:
        scored = sorted(
            (r for r in results if r.weighted_score is not None),
            key=lambda r: r.weighted_score or 0,
        )
        strengths = [s for r in reversed(scored) for s in r.strengths[:1]]
        improvements = [g for r in scored for g in r.gaps[:1]]
        topics = [p for r in scored for p in r.missed_points[:2]]
        return {
            "skills": {},
            "strengths": list(dict.fromkeys(strengths))[:3],
            "improvements": list(dict.fromkeys(improvements))[:3],
            "topics": list(dict.fromkeys(topics))[:5],
        }
