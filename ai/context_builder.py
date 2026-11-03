"""Bounded planner context: only the sections the planner needs, for the target level only.

Blocks carry a priority; when the budget is exceeded, lower-priority blocks are dropped first:
  0 role round structure + level guidance + interviewer guidance; skill level guidance; seeds
  1 skill positive signals / pitfalls
  2 skill core knowledge
  3 role probes / signals / pitfalls
Seeds are added round-robin across skills so every skill keeps its first seeds under pressure.
The included seed ids are recorded so the planner's output can be validated against them.
"""

from dataclasses import dataclass
from itertools import zip_longest

from ai.playbook_loader import PlaybookLibrary
from ai.schemas.enums import Level
from ai.schemas.interview import PlaybookSelection
from ai.schemas.playbook import QuestionSeed

DEFAULT_BUDGET_CHARS = 24_000


@dataclass(frozen=True)
class PlannerContext:
    text: str
    seed_ids: frozenset[str]
    dropped_blocks: int

    @property
    def truncated(self) -> bool:
        return self.dropped_blocks > 0


@dataclass(frozen=True)
class _Block:
    priority: int
    order: tuple[int, int, int]
    text: str
    seed_id: str | None = None


def _seed_block(seed: QuestionSeed) -> str:
    lines = [
        f"- seed_id: {seed.id}",
        f"  question: {seed.question}",
        f"  objective: {seed.objective}",
        "  expected_points:",
        *(f"    - {point}" for point in seed.expected_points),
        "  followup_probes:",
        *(f"    - {probe}" for probe in seed.followup_probes),
    ]
    if seed.scoring_caution:
        lines.append(f"  scoring_caution: {seed.scoring_caution}")
    return "\n".join(lines)


def build_planner_context(
    library: PlaybookLibrary,
    selection: PlaybookSelection,
    level: Level,
    *,
    budget_chars: int = DEFAULT_BUDGET_CHARS,
) -> PlannerContext:
    role = library.roles[selection.role_playbook.id]
    blocks: list[_Block] = []

    def add(priority: int, section: int, index: int, sub: int, text: str, seed_id=None) -> None:
        if text.strip():
            blocks.append(_Block(priority, (section, index, sub), text.strip(), seed_id))

    add(
        0,
        0,
        0,
        0,
        f"## Role playbook: {role.title}\n### Round Structure\n"
        f"{role.sections.get('Round Structure', '')}",
    )
    add(0, 0, 0, 1, f"### Level guidance ({level.value})\n{role.level_guidance.get(level, '')}")
    add(0, 0, 0, 2, f"### Interviewer Guidance\n{role.sections.get('Interviewer Guidance', '')}")
    add(3, 0, 0, 3, f"### Interviewer Probes\n{role.sections.get('Interviewer Probes', '')}")
    add(3, 0, 0, 4, f"### Positive Signals\n{role.sections.get('Positive Signals', '')}")
    add(3, 0, 0, 5, f"### Pitfalls\n{role.sections.get('Pitfalls', '')}")

    seed_lists: list[list[QuestionSeed]] = []
    for index, selected in enumerate(selection.skills, start=1):
        skill = library.skills[selected.id]
        add(
            0,
            1,
            index,
            0,
            f"## Skill {selected.id} — {skill.title} "
            f"(target_questions: {selected.target_questions})\n"
            f"### Level guidance ({level.value})\n{skill.level_guidance.get(level, '')}",
        )
        add(2, 1, index, 1, f"### Core Knowledge\n{skill.sections.get('Core Knowledge', '')}")
        add(1, 1, index, 2, f"### Positive Signals\n{skill.sections.get('Positive Signals', '')}")
        add(1, 1, index, 3, f"### Pitfalls\n{skill.sections.get('Pitfalls', '')}")
        add(0, 1, index, 4, "### Question seeds")
        seed_lists.append(skill.seeds_for_level(level))

    # Round-robin so that, under budget pressure, each skill keeps its first seeds.
    for rank, row in enumerate(zip_longest(*seed_lists)):
        for skill_index, seed in enumerate(row, start=1):
            if seed is not None:
                add(0, 1, skill_index, 10 + rank, _seed_block(seed), seed.id)

    included: list[_Block] = []
    used = 0
    for block in sorted(blocks, key=lambda b: (b.priority, b.order[2] >= 10, b.order[2], b.order)):
        cost = len(block.text) + 2
        if used + cost <= budget_chars:
            included.append(block)
            used += cost
    included.sort(key=lambda b: b.order)

    return PlannerContext(
        text="\n\n".join(block.text for block in included),
        seed_ids=frozenset(b.seed_id for b in included if b.seed_id),
        dropped_blocks=len(blocks) - len(included),
    )
