from pathlib import Path

import pytest

from ai.playbook_loader import Issue, load_library
from ai.playbooks.lint import lint_library, main

RAG = Path("competencies/ai_engineer/rag_systems.md")
ROLE = Path("roles/ai_engineer.md")


def _errors(issues: list[Issue]) -> set[str]:
    return {issue.code for issue in issues if issue.severity == "error"}


def _lint(playbooks: Path, config: Path, *, strict: bool = False) -> list[Issue]:
    return lint_library(load_library(playbooks, config), strict=strict)


def _edit(path: Path, old: str, new: str, count: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    assert text.count(old) >= count, f"{old!r} not found in {path.name}"
    path.write_text(text.replace(old, new), encoding="utf-8")


def test_real_library_passes_default_mode() -> None:
    issues = lint_library(load_library())
    assert _errors(issues) == set(), [str(i) for i in issues]
    assert main([]) == 0


def test_strict_mode_turns_missing_files_and_drafts_into_errors() -> None:
    issues = lint_library(load_library(), strict=True)
    assert {"missing-skill", "missing-playbook", "draft"} <= _errors(issues)
    assert main(["--strict"]) == 1


def test_rubric_weights_must_sum_to_one(library_copy) -> None:
    playbooks, config = library_copy
    _edit(playbooks / RAG, "- completeness: 0.25", "- completeness: 0.30")
    assert "rubric-weights" in _errors(_lint(playbooks, config))


def test_rubric_criterion_must_exist(library_copy) -> None:
    playbooks, config = library_copy
    _edit(playbooks / RAG, "- practical_examples: 0.15", "- creativity: 0.15")
    assert "rubric-criterion" in _errors(_lint(playbooks, config))


def test_rubric_criterion_must_match_assessment(library_copy) -> None:
    playbooks, config = library_copy
    _edit(playbooks / RAG, "- practical_examples: 0.15", "- clarity: 0.15")
    assert "rubric-criterion" in _errors(_lint(playbooks, config))


def test_required_section_missing(library_copy) -> None:
    playbooks, config = library_copy
    _edit(playbooks / RAG, "## Pitfalls", "## Pitfall")
    errors = _errors(_lint(playbooks, config))
    assert "missing-section" in errors


def test_level_guidance_must_cover_every_level(library_copy) -> None:
    playbooks, config = library_copy
    _edit(playbooks / ROLE, "### Junior", "### Senior")
    assert "level-guidance" in _errors(_lint(playbooks, config))


def test_seed_requires_all_fields(library_copy) -> None:
    playbooks, config = library_copy
    _edit(playbooks / RAG, "**Objective:** Hiểu mục đích", "Hiểu mục đích")
    assert "seed-field" in _errors(_lint(playbooks, config))


def test_seed_heading_format(library_copy) -> None:
    playbooks, config = library_copy
    _edit(playbooks / RAG, "### rag_basics_01 — ", "### RAG basics: ")
    assert "seed-heading" in _errors(_lint(playbooks, config))


def test_seed_ids_are_unique_across_files(library_copy) -> None:
    playbooks, config = library_copy
    copy = playbooks / "competencies" / "extra" / "rag_copy.md"
    copy.parent.mkdir()
    copy.write_text(
        (playbooks / RAG).read_text(encoding="utf-8").replace("id: rag_systems", "id: rag_copy"),
        encoding="utf-8",
    )
    assert "duplicate-seed" in _errors(_lint(playbooks, config))


def test_frontmatter_schema_is_validated(library_copy) -> None:
    playbooks, config = library_copy
    _edit(playbooks / RAG, "version: 1.0.0", "version: 1.0")
    assert "frontmatter-schema" in _errors(_lint(playbooks, config))


def test_file_name_must_match_id(library_copy) -> None:
    playbooks, config = library_copy
    (playbooks / RAG).rename(playbooks / RAG.with_name("rag.md"))
    assert "file-name" in _errors(_lint(playbooks, config))


def test_catalog_weights_must_sum_to_one(library_copy) -> None:
    playbooks, config = library_copy
    _edit(
        config / "competency_catalog.yaml",
        "sql: { weight: 0.40, core: true }",
        "sql: { weight: 0.50, core: true }",
    )
    assert "catalog-weights" in _errors(_lint(playbooks, config))


def test_catalog_level_must_be_supported_by_skill(library_copy) -> None:
    playbooks, config = library_copy
    _edit(playbooks / RAG, "levels: [intern, fresher, junior]", "levels: [fresher, junior]")
    _edit(playbooks / RAG, "**Levels:** intern, fresher", "**Levels:** fresher", count=2)
    issues = _lint(playbooks, config)
    assert "catalog-level" in _errors(issues)


@pytest.mark.parametrize("strict", [False, True])
def test_unparseable_config_is_an_error(library_copy, strict: bool) -> None:
    playbooks, config = library_copy
    (config / "rubric_criteria.yaml").write_text("version: [", encoding="utf-8")
    assert "yaml" in _errors(_lint(playbooks, config, strict=strict))
