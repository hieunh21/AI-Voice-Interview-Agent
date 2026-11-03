import math

from ai.playbook_loader import load_library
from ai.schemas.enums import Assessment, Level, Role


def test_real_library_loads_without_errors() -> None:
    library = load_library()
    errors = [str(i) for i in library.issues if i.severity == "error"]
    assert errors == []
    assert library.catalog is not None
    assert library.criteria is not None


def test_role_playbook_sections_and_level_guidance() -> None:
    playbook = load_library().roles["role_ai_engineer"]
    assert playbook.meta.role is Role.AI_ENGINEER
    assert set(playbook.level_guidance) == set(Level)
    assert "Interviewer Guidance" in playbook.sections
    assert len(playbook.content_sha256) == 64
    assert playbook.ref.id == "role_ai_engineer"


def test_competency_skill_seeds_rubric_and_references() -> None:
    skill = load_library().skills["rag_systems"]
    assert skill.meta.assessment is Assessment.QUESTION
    assert "bm25" in skill.meta.keywords

    seed_ids = [seed.id for seed in skill.seeds]
    assert len(seed_ids) == len(set(seed_ids)) >= 2
    hybrid = next(seed for seed in skill.seeds if seed.id == "rag_hybrid_01")
    assert hybrid.levels == [Level.FRESHER, Level.JUNIOR]
    assert len(hybrid.expected_points) >= 2
    assert hybrid.followup_probes
    assert hybrid.question.startswith("Khi nào nên dùng hybrid retrieval")

    for level in skill.meta.levels:
        assert skill.seeds_for_level(level), f"no seed for {level}"

    assert math.isclose(sum(c.weight for c in skill.rubric), 1.0)
    assert {c.criterion_id for c in skill.rubric} == {
        "technical_accuracy",
        "completeness",
        "reasoning",
        "practical_examples",
    }
    assert all("https://" in ref for ref in skill.references)


def test_content_hash_ignores_line_ending_style(library_copy) -> None:
    playbooks, config = library_copy
    original = load_library(playbooks, config).skills["rag_systems"].content_sha256
    path = playbooks / "competencies" / "ai_engineer" / "rag_systems.md"
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    assert load_library(playbooks, config).skills["rag_systems"].content_sha256 == original


def test_catalog_covers_every_role_and_level() -> None:
    catalog = load_library().catalog
    assert catalog is not None
    assert set(catalog.roles) == set(Role)
    for role_cfg in catalog.roles.values():
        assert set(role_cfg.levels) == set(Level)
