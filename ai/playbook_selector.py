"""Rule-based playbook selection (no LLM): role/level/mode + optional CV/JD → PlaybookSelection.

- Core skills of the role-level are always selected; a missing/unusable core skill is a
  configuration error that blocks planning (never silently replaced).
- Optional skills are ranked by catalog weight plus a boost when the JD (stronger) or CV mentions
  one of the skill's keywords. Documents can add one extra skill within the mode's budget.
- Questions are allocated with the D'Hondt method: every skill gets one, the rest go to the
  highest score / (allocated + 1). Deterministic and explainable.
"""

import logging
import re
from dataclasses import dataclass, field
from functools import cache

from ai.playbook_loader import PlaybookLibrary
from ai.schemas.catalog import SkillWeight
from ai.schemas.enums import Assessment, InterviewMode, Level, PlaybookStatus, Role
from ai.schemas.interview import PlaybookSelection, SelectedSkill
from ai.schemas.playbook import CompetencySkill

logger = logging.getLogger(__name__)

JD_BOOST = 0.20
CV_BOOST = 0.10
MAX_REASON_KEYWORDS = 3


class SelectionError(Exception):
    """The library/catalog cannot produce a valid selection (configuration problem)."""


@dataclass(frozen=True)
class DocumentSignals:
    """Text used for keyword matching: raw CV/JD plus terms extracted by the analyser."""

    cv_text: str = ""
    jd_text: str = ""
    cv_terms: tuple[str, ...] = ()
    jd_terms: tuple[str, ...] = ()

    @property
    def cv_corpus(self) -> str:
        return "\n".join([self.cv_text, *self.cv_terms])

    @property
    def jd_corpus(self) -> str:
        return "\n".join([self.jd_text, *self.jd_terms])


@dataclass
class _Candidate:
    skill: CompetencySkill
    config: SkillWeight
    score: float
    capacity: int  # seeds available at the target level
    reasons: list[str] = field(default_factory=list)
    boosted: bool = False
    questions: int = 0


@cache
def _keyword_pattern(keyword: str) -> re.Pattern[str]:
    return re.compile(rf"(?<!\w){re.escape(keyword)}(?!\w)", re.IGNORECASE)


def keyword_hits(text: str, keywords: list[str]) -> list[str]:
    if not text:
        return []
    return [k for k in keywords if _keyword_pattern(k).search(text)]


def is_usable(status: PlaybookStatus, *, allow_draft: bool) -> bool:
    return status is PlaybookStatus.REVIEWED or (allow_draft and status is PlaybookStatus.DRAFT)


def allocate_questions(scores: list[float], capacities: list[int], total: int) -> list[int]:
    """D'Hondt allocation, one question minimum per skill, never above a skill's seed capacity.

    Ties go to the earlier skill. Raises if the skills cannot hold `total` questions.
    """
    if total < len(scores) or sum(capacities) < total or min(capacities, default=0) < 1:
        raise SelectionError(f"skills cannot hold {total} questions (capacity {capacities})")
    counts = [1] * len(scores)
    for _ in range(total - len(scores)):
        open_slots = [i for i in range(len(scores)) if counts[i] < capacities[i]]
        best = max(open_slots, key=lambda i: (scores[i] / (counts[i] + 1), -i))
        counts[best] += 1
    return counts


def select_playbooks(
    library: PlaybookLibrary,
    *,
    role: Role,
    level: Level,
    mode: InterviewMode,
    allow_draft: bool,
    signals: DocumentSignals | None = None,
) -> PlaybookSelection:
    catalog = library.catalog
    if catalog is None:
        raise SelectionError("competency catalog is not loaded")
    signals = signals or DocumentSignals()
    mode_cfg = catalog.modes[mode]
    role_cfg = catalog.roles[role]
    level_cfg = role_cfg.levels[level]

    playbook = library.roles.get(role_cfg.playbook)
    if playbook is None or not is_usable(playbook.meta.status, allow_draft=allow_draft):
        raise SelectionError(f"role playbook {role_cfg.playbook} is missing or not reviewed")

    candidates: list[_Candidate] = []
    for skill_id, config in level_cfg.skills.items():
        skill = library.skills.get(skill_id)
        usable = (
            skill is not None
            and skill.meta.assessment is Assessment.QUESTION
            and is_usable(skill.meta.status, allow_draft=allow_draft)
            and bool(skill.seeds_for_level(level))
        )
        if not usable or skill is None:
            if config.core:
                raise SelectionError(f"core skill {skill_id} is unavailable for {role}/{level}")
            logger.warning(
                "Skipping optional skill %s for %s/%s: unavailable", skill_id, role, level
            )
            continue

        keywords = list(skill.meta.keywords)
        jd_hits = keyword_hits(signals.jd_corpus, keywords)
        cv_hits = keyword_hits(signals.cv_corpus, keywords)
        reasons = ["Kỹ năng cốt lõi của vị trí"] if config.core else []
        if jd_hits:
            reasons.append(f"JD nhắc tới: {', '.join(jd_hits[:MAX_REASON_KEYWORDS])}")
        if cv_hits:
            reasons.append(f"CV nhắc tới: {', '.join(cv_hits[:MAX_REASON_KEYWORDS])}")
        score = config.weight + (JD_BOOST if jd_hits else 0.0) + (CV_BOOST if cv_hits else 0.0)
        candidates.append(
            _Candidate(
                skill,
                config,
                score,
                capacity=len(skill.seeds_for_level(level)),
                reasons=reasons,
                boosted=bool(jd_hits or cv_hits),
            )
        )

    core = sorted((c for c in candidates if c.config.core), key=lambda c: -c.score)
    optional = sorted(
        (c for c in candidates if not c.config.core), key=lambda c: (-c.score, c.skill.meta.id)
    )
    wanted = mode_cfg.skills.min + (1 if any(c.boosted for c in optional) else 0)
    count = min(max(wanted, len(core)), mode_cfg.skills.max, len(candidates))
    if count < mode_cfg.skills.min:
        raise SelectionError(f"only {len(candidates)} usable skills for {role}/{level}/{mode}")
    chosen = core + optional[: count - len(core)]
    # Add skills while the chosen ones do not have enough seeds to fill the mode.
    spare = optional[count - len(core) :]
    while (
        sum(c.capacity for c in chosen) < mode_cfg.main_questions
        and spare
        and len(chosen) < mode_cfg.skills.max
    ):
        chosen.append(spare.pop(0))

    for candidate, questions in zip(
        chosen,
        allocate_questions(
            [c.score for c in chosen], [c.capacity for c in chosen], mode_cfg.main_questions
        ),
        strict=True,
    ):
        candidate.questions = questions

    cross_cutting = []
    for skill_id in catalog.cross_cutting_skills:
        skill = library.skills.get(skill_id)
        if skill is not None and is_usable(skill.meta.status, allow_draft=allow_draft):
            cross_cutting.append(skill.ref)
        else:
            logger.warning("Cross-cutting skill %s unavailable; it will not be scored", skill_id)

    return PlaybookSelection(
        role=role,
        level=level,
        mode=mode,
        role_playbook=playbook.ref,
        skills=[
            SelectedSkill(
                id=c.skill.meta.id,
                title=c.skill.title,
                version=c.skill.meta.version,
                content_sha256=c.skill.content_sha256,
                is_core=c.config.core,
                target_questions=c.questions,
                reasons=c.reasons or ["Phù hợp với vị trí và cấp độ"],
                weight=c.config.weight,
            )
            for c in chosen
        ],
        cross_cutting=cross_cutting,
    )


def unmatched_requirements(
    library: PlaybookLibrary, requirements: list[str], skill_ids: list[str]
) -> list[str]:
    """JD requirements that none of `skill_ids` covers (shown as an out-of-scope warning)."""
    keywords = [
        k
        for skill_id in skill_ids
        if skill_id in library.skills
        for k in library.skills[skill_id].meta.keywords
    ]
    unmatched = []
    for requirement in requirements:
        if not any(_keyword_pattern(k).search(requirement) for k in keywords):
            unmatched.append(requirement)
    return unmatched
