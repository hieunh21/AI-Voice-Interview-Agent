"""Turn a PlaybookSelection into a frozen InterviewPlan.

The LLM only *proposes* questions. Every proposal is validated against the reviewed playbook:
- seed-based questions take expected points, probes and scoring caution from the seed itself
  (the LLM may rephrase the question text, never the scoring content);
- CV/JD questions must be grounded in the validated document analysis, and are capped so that
  reviewed seeds dominate every plan;
- invalid, duplicate or surplus proposals are dropped and missing slots are filled from unused
  seeds, so the plan always matches the allocation exactly.
Rubric weights always come from the skill file, never from the model.
"""

import logging
import random
from dataclasses import dataclass

from ai.context_builder import PlannerContext
from ai.llm.base import StructuredLLM
from ai.nodes.document_analysis import appears_in
from ai.playbook_loader import PlaybookLibrary
from ai.prompts import planner as planner_prompt
from ai.schemas.catalog import CriterionDefinition
from ai.schemas.documents import DocumentAnalysis
from ai.schemas.enums import Level, QuestionOrigin
from ai.schemas.interview import (
    CrossCuttingSkill,
    InterviewLimits,
    InterviewPlan,
    InterviewSetup,
    PlannedQuestion,
    PlanVersions,
    PlaybookSelection,
)
from ai.schemas.playbook import CompetencySkill, QuestionSeed

logger = logging.getLogger(__name__)

DETERMINISTIC_MODEL = "deterministic"
MAX_DOC_CHARS_IN_PROMPT = 8_000
_LEVEL_ORDER = {Level.INTERN: 0, Level.FRESHER: 1, Level.JUNIOR: 2}


@dataclass(frozen=True)
class PlanInputs:
    library: PlaybookLibrary
    selection: PlaybookSelection
    setup: InterviewSetup
    analysis: DocumentAnalysis


@dataclass(frozen=True)
class _Draft:
    skill_id: str
    origin: QuestionOrigin
    seed_id: str | None
    text: str
    objective: str
    note: str | None
    expected: tuple[str, ...]
    hints: tuple[str, ...]
    caution: str | None


def _difficulty(seed: QuestionSeed) -> int:
    return min(_LEVEL_ORDER[level] for level in seed.levels)


def _seed_draft(skill_id: str, seed: QuestionSeed, text: str | None = None) -> _Draft:
    return _Draft(
        skill_id=skill_id,
        origin=QuestionOrigin.SEED if text is None else QuestionOrigin.SEED_ADAPTED,
        seed_id=seed.id,
        text=text or seed.question,
        objective=seed.objective,
        note=None,
        expected=tuple(seed.expected_points),
        hints=tuple(seed.followup_probes),
        caution=seed.scoring_caution,
    )


def max_personalised(main_questions: int) -> int:
    return max(1, main_questions // 3)


def deterministic_drafts(inputs: PlanInputs, rng: random.Random) -> list[_Draft]:
    """Seed-only plan: varied per session (seeded RNG), easier seeds first within each skill."""
    level = inputs.setup.level
    drafts: list[_Draft] = []
    for selected in inputs.selection.skills:
        seeds = inputs.library.skills[selected.id].seeds_for_level(level)
        chosen = rng.sample(seeds, k=min(selected.target_questions, len(seeds)))
        chosen.sort(key=lambda s: (_difficulty(s), seeds.index(s)))
        drafts.extend(_seed_draft(selected.id, seed) for seed in chosen)
    return drafts


def _grounded(text: str, terms: list[str]) -> bool:
    return any(len(t) >= 2 and appears_in(t, text) for t in terms)


def validate_llm_drafts(
    out: planner_prompt.PlannerOutput, inputs: PlanInputs, rng: random.Random
) -> list[_Draft]:
    library, setup, analysis = inputs.library, inputs.setup, inputs.analysis
    quotas = {s.id: s.target_questions for s in inputs.selection.skills}
    used_seeds: set[str] = set()
    kept: list[_Draft] = []
    personalised = 0
    cap = max_personalised(sum(quotas.values()))

    cv_terms = []
    if analysis.candidate is not None:
        cv_terms = [p.name for p in analysis.candidate.projects] + analysis.candidate.skills
    jd_terms = []
    if analysis.job is not None:
        jd_terms = analysis.job.required_skills + analysis.job.nice_to_have

    for q in out.questions:
        skill: CompetencySkill | None = library.skills.get(q.skill_id)
        if skill is None or q.skill_id not in quotas:
            continue
        if sum(d.skill_id == q.skill_id for d in kept) >= quotas[q.skill_id]:
            continue
        text = " ".join(q.question_text.split())

        if q.origin in ("seed", "seed_adapted"):
            seed = next(
                (s for s in skill.seeds_for_level(setup.level) if s.id == q.source_seed_id), None
            )
            if seed is None or seed.id in used_seeds:
                continue
            adapted = q.origin == "seed_adapted" and 5 <= len(text) <= 400
            kept.append(_seed_draft(skill.meta.id, seed, text if adapted else None))
            used_seeds.add(seed.id)
            continue

        # CV / JD personalised question.
        note = " ".join(q.personalization_note.split())
        expected = tuple(p.strip() for p in q.expected_points if p.strip())[:6]
        has_doc = setup.cv_text if q.origin == "cv" else setup.jd_text
        terms = cv_terms if q.origin == "cv" else jd_terms
        if (
            personalised >= cap
            or not has_doc
            or not note
            or len(expected) < 2
            or not 5 <= len(text) <= 400
            or not _grounded(f"{text} {note}", terms)
        ):
            continue
        kept.append(
            _Draft(
                skill_id=skill.meta.id,
                origin=QuestionOrigin(q.origin),
                seed_id=None,
                text=text,
                objective=" ".join(q.objective.split()) or f"Đánh giá {skill.title} qua tài liệu",
                note=note[:300],
                expected=expected,
                hints=tuple(h.strip() for h in q.followup_hints if h.strip())[:4],
                caution=None,
            )
        )
        personalised += 1

    # Fill missing slots with unused seeds, placed after the skill's last kept question.
    for selected in inputs.selection.skills:
        missing = selected.target_questions - sum(d.skill_id == selected.id for d in kept)
        if missing <= 0:
            continue
        seeds = [
            s
            for s in library.skills[selected.id].seeds_for_level(setup.level)
            if s.id not in used_seeds
        ]
        fill = rng.sample(seeds, k=min(missing, len(seeds)))
        fill.sort(key=_difficulty)
        last = max(
            (i for i, d in enumerate(kept) if d.skill_id == selected.id), default=len(kept) - 1
        )
        for offset, seed in enumerate(fill, start=1):
            kept.insert(last + offset, _seed_draft(selected.id, seed))
            used_seeds.add(seed.id)
        logger.info("Planner left %d slot(s) for %s; filled from seeds", missing, selected.id)
    return kept


async def propose_with_llm(
    llm: StructuredLLM, inputs: PlanInputs, context: PlannerContext
) -> planner_prompt.PlannerOutput:
    setup = inputs.setup
    return await llm.generate(
        system=planner_prompt.SYSTEM,
        prompt=planner_prompt.build_prompt(
            selection=inputs.selection,
            context=context.text,
            analysis=inputs.analysis,
            cv_text=(setup.cv_text or "")[:MAX_DOC_CHARS_IN_PROMPT] or None,
            jd_text=(setup.jd_text or "")[:MAX_DOC_CHARS_IN_PROMPT] or None,
        ),
        schema=planner_prompt.PlannerOutput,
        temperature=0.4,
    )


def _frozen_criteria(inputs: PlanInputs) -> dict[str, CriterionDefinition]:
    criteria = inputs.library.criteria
    if criteria is None:
        raise ValueError("rubric criteria are not loaded")
    ids = {
        c.criterion_id for s in inputs.selection.skills for c in inputs.library.skills[s.id].rubric
    }
    ids |= {
        c.criterion_id
        for ref in inputs.selection.cross_cutting
        for c in inputs.library.skills[ref.id].rubric
    }
    return {cid: criteria.criteria[cid] for cid in sorted(ids)}


def assemble_plan(
    drafts: list[_Draft],
    inputs: PlanInputs,
    *,
    planner_model: str,
    warnings: list[str],
) -> InterviewPlan:
    library, selection, setup = inputs.library, inputs.selection, inputs.setup
    catalog, criteria = library.catalog, library.criteria
    if catalog is None or criteria is None:
        raise ValueError("catalog and rubric criteria must be loaded")
    mode_cfg = catalog.modes[setup.mode]

    questions = [
        PlannedQuestion(
            question_id=f"q_{index:03d}",
            skill_id=draft.skill_id,
            origin=draft.origin,
            source_seed_id=draft.seed_id,
            question_text=draft.text,
            objective=draft.objective,
            personalization_note=draft.note,
            expected_points=list(draft.expected),
            followup_hints=list(draft.hints),
            scoring_caution=draft.caution,
            rubric=library.skills[draft.skill_id].rubric,
        )
        for index, draft in enumerate(drafts, start=1)
    ]
    cross_cutting = [
        CrossCuttingSkill(
            id=ref.id,
            title=library.skills[ref.id].title,
            version=ref.version,
            content_sha256=ref.content_sha256,
            rubric=library.skills[ref.id].rubric,
        )
        for ref in selection.cross_cutting
    ]
    return InterviewPlan(
        role=setup.role,
        level=setup.level,
        mode=setup.mode,
        input_sources=setup.input_sources,
        role_playbook=selection.role_playbook,
        selected_skills=selection.skills,
        cross_cutting_skills=cross_cutting,
        rubric_criteria=_frozen_criteria(inputs),
        questions=questions,
        limits=InterviewLimits(
            main_questions=mode_cfg.main_questions,
            max_followups_per_question=mode_cfg.max_followups_per_question,
            max_turns=mode_cfg.max_turns,
            time_budget_minutes=mode_cfg.time_budget_minutes,
        ),
        versions=PlanVersions(
            catalog=catalog.version,
            rubric=criteria.version,
            planner_prompt=planner_prompt.PLANNER_PROMPT_VERSION,
            planner_model=planner_model,
        ),
        warnings=list(dict.fromkeys(warnings)),
    )
