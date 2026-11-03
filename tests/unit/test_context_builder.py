from ai.context_builder import build_planner_context
from ai.playbook_loader import load_library
from ai.playbook_selector import select_playbooks
from ai.schemas.enums import InterviewMode, Level, Role

LIBRARY = load_library()


def _selection(level: Level = Level.INTERN):
    return select_playbooks(
        LIBRARY,
        role=Role.AI_ENGINEER,
        level=level,
        mode=InterviewMode.STANDARD,
        allow_draft=True,
    )


def test_context_contains_only_target_level_material() -> None:
    selection = _selection(Level.INTERN)
    context = build_planner_context(LIBRARY, selection, Level.INTERN, budget_chars=100_000)
    assert not context.truncated
    expected = {
        seed.id
        for s in selection.skills
        for seed in LIBRARY.skills[s.id].seeds_for_level(Level.INTERN)
    }
    assert context.seed_ids == expected
    assert "Level guidance (intern)" in context.text
    assert "### Junior" not in context.text
    assert "ml_05" not in context.text  # junior-only seed of a selected skill


def test_budget_drops_low_priority_blocks_but_keeps_seeds_for_every_skill() -> None:
    selection = _selection(Level.FRESHER)
    full = build_planner_context(LIBRARY, selection, Level.FRESHER, budget_chars=100_000)
    tight = build_planner_context(LIBRARY, selection, Level.FRESHER, budget_chars=6_000)
    assert len(tight.text) <= 6_000
    assert tight.truncated
    assert "Core Knowledge" in full.text
    assert "Core Knowledge" not in tight.text
    for selected in selection.skills:
        skill_seeds = {s.id for s in LIBRARY.skills[selected.id].seeds_for_level(Level.FRESHER)}
        assert skill_seeds & tight.seed_ids, f"no seed kept for {selected.id}"
