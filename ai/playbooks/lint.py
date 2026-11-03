"""Playbook linter: `python -m ai.playbooks.lint [--strict]`.

Default mode validates everything that exists and reports not-yet-written files and draft content
as warnings, so the library can be built incrementally. `--strict` is the production gate: every
file referenced by the catalog must exist and every loaded playbook must be `status: reviewed`.
"""

import argparse
import io
import math
import sys
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

from ai import CONFIG_DIR, PLAYBOOKS_DIR
from ai.playbook_loader import Issue, PlaybookLibrary, load_library
from ai.schemas.common import WEIGHT_TOLERANCE
from ai.schemas.enums import Assessment, InterviewMode, Level, PlaybookStatus, Role

MIN_CORE_SKILLS = 2


class _Report:
    def __init__(self, issues: list[Issue], strict: bool) -> None:
        self.issues = issues
        self.strict = strict

    def error(self, code: str, path: str, message: str) -> None:
        self.issues.append(Issue("error", code, path, message))

    def warn(self, code: str, path: str, message: str) -> None:
        self.issues.append(Issue("warning", code, path, message))

    def gate(self, code: str, path: str, message: str) -> None:
        """Warning while the library is being built; error under --strict."""
        self.issues.append(Issue("error" if self.strict else "warning", code, path, message))


def _check_criteria_usage(lib: PlaybookLibrary, report: _Report) -> None:
    if lib.criteria is None:
        return
    for skill in lib.skills.values():
        for criterion in skill.rubric:
            definition = lib.criteria.criteria.get(criterion.criterion_id)
            if definition is None:
                report.error(
                    "rubric-criterion",
                    skill.path,
                    f"unknown criterion '{criterion.criterion_id}' (define it in "
                    f"{lib.criteria_path})",
                )
            elif definition.applies_to is not skill.meta.assessment:
                report.error(
                    "rubric-criterion",
                    skill.path,
                    f"criterion '{criterion.criterion_id}' applies to "
                    f"'{definition.applies_to.value}' skills, not '{skill.meta.assessment.value}'",
                )


def _check_seed_uniqueness(lib: PlaybookLibrary, report: _Report) -> None:
    owner: dict[str, str] = {}
    for skill in lib.skills.values():
        for seed in skill.seeds:
            if seed.id in owner:
                report.error(
                    "duplicate-seed",
                    skill.path,
                    f"seed id '{seed.id}' is also used in {owner[seed.id]}",
                )
            else:
                owner[seed.id] = skill.path


def _check_catalog(lib: PlaybookLibrary, report: _Report) -> None:
    catalog = lib.catalog
    if catalog is None:
        return
    path = lib.catalog_path

    for mode in InterviewMode:
        if mode not in catalog.modes:
            report.error("catalog-coverage", path, f"mode '{mode.value}' is not configured")
    for level in Level:
        if level not in catalog.levels:
            report.error("catalog-coverage", path, f"level '{level.value}' has no display info")
    if not catalog.modes:
        return
    max_core = min(m.skills.max for m in catalog.modes.values())
    min_listed = max(m.skills.min for m in catalog.modes.values())

    missing_skills: dict[str, list[str]] = defaultdict(list)
    referenced_playbooks: set[str] = set()

    for role in Role:
        role_cfg = catalog.roles.get(role)
        if role_cfg is None:
            report.error("catalog-coverage", path, f"role '{role.value}' is not configured")
            continue
        expected_playbook = f"role_{role.value}"
        referenced_playbooks.add(role_cfg.playbook)
        if role_cfg.playbook != expected_playbook:
            report.error(
                "catalog-playbook",
                path,
                f"roles.{role.value}.playbook must be '{expected_playbook}'",
            )
        playbook = lib.roles.get(role_cfg.playbook)
        if playbook is None:
            report.gate(
                "missing-playbook",
                path,
                f"role playbook '{role_cfg.playbook}' not found (expected "
                f"playbooks/roles/{role.value}.md)",
            )
        else:
            uncovered = [lv.value for lv in Level if lv not in playbook.meta.levels]
            if uncovered:
                report.error(
                    "playbook-levels", playbook.path, f"must cover every level; missing {uncovered}"
                )
            if playbook.meta.status is PlaybookStatus.DEPRECATED:
                report.error("deprecated", playbook.path, "a deprecated playbook is still in use")

        for level in Level:
            where = f"roles.{role.value}.levels.{level.value}"
            level_cfg = role_cfg.levels.get(level)
            if level_cfg is None:
                report.error("catalog-coverage", path, f"{where} is not configured")
                continue

            total = math.fsum(s.weight for s in level_cfg.skills.values())
            if abs(total - 1.0) > WEIGHT_TOLERANCE:
                report.error(
                    "catalog-weights", path, f"{where}: weights sum to {total:.4f}, expected 1.0"
                )
            core = level_cfg.core_skills
            if not MIN_CORE_SKILLS <= len(core) <= max_core:
                report.error(
                    "catalog-core",
                    path,
                    f"{where}: has {len(core)} core skills; need {MIN_CORE_SKILLS}..{max_core} "
                    "(at least 2, and no more than the smallest mode can ask)",
                )
            if len(level_cfg.skills) < min_listed:
                report.error(
                    "catalog-skills",
                    path,
                    f"{where}: lists {len(level_cfg.skills)} skills; every mode needs at least "
                    f"{min_listed} to choose from",
                )

            for skill_id in level_cfg.skills:
                if skill_id in catalog.cross_cutting_skills:
                    report.error(
                        "catalog-skill",
                        path,
                        f"{where}: '{skill_id}' is cross-cutting and cannot take question slots",
                    )
                    continue
                skill = lib.skills.get(skill_id)
                if skill is None:
                    missing_skills[skill_id].append(f"{role.value}/{level.value}")
                    continue
                if skill.meta.assessment is not Assessment.QUESTION:
                    report.error(
                        "catalog-skill", path, f"{where}: '{skill_id}' is not a question skill"
                    )
                if level not in skill.meta.levels:
                    report.error(
                        "catalog-level",
                        path,
                        f"{where}: skill '{skill_id}' does not support level '{level.value}'",
                    )
                if skill.meta.status is PlaybookStatus.DEPRECATED:
                    report.error("deprecated", skill.path, f"deprecated but referenced by {where}")

    for skill_id in catalog.cross_cutting_skills:
        skill = lib.skills.get(skill_id)
        if skill is None:
            missing_skills[skill_id].append("cross_cutting_skills")
        elif skill.meta.assessment is not Assessment.CROSS_CUTTING:
            report.error(
                "catalog-skill",
                path,
                f"cross_cutting_skills: '{skill_id}' must declare assessment: cross_cutting",
            )

    for skill_id, uses in sorted(missing_skills.items()):
        report.gate(
            "missing-skill",
            path,
            f"skill '{skill_id}' has no Markdown file yet (used by {', '.join(uses)})",
        )

    referenced_skills = set(catalog.cross_cutting_skills) | {
        skill_id
        for role_cfg in catalog.roles.values()
        for level_cfg in role_cfg.levels.values()
        for skill_id in level_cfg.skills
    }
    for skill_id, skill in lib.skills.items():
        if skill_id not in referenced_skills:
            report.warn("orphan", skill.path, "not referenced by the competency catalog")
    for playbook_id, playbook in lib.roles.items():
        if playbook_id not in referenced_playbooks:
            report.warn("orphan", playbook.path, "not referenced by the competency catalog")


def _check_status_and_references(lib: PlaybookLibrary, report: _Report) -> None:
    documents = [(p.path, p.meta.status) for p in lib.roles.values()] + [
        (s.path, s.meta.status) for s in lib.skills.values()
    ]
    for path, status in documents:
        if status is PlaybookStatus.DRAFT:
            report.gate(
                "draft",
                path,
                "status is draft — review the content, then set 'status: reviewed'",
            )
    for skill in lib.skills.values():
        for reference in skill.references:
            if "http://" not in reference and "https://" not in reference:
                report.warn("reference-url", skill.path, f"reference has no URL: '{reference}'")


def lint_library(lib: PlaybookLibrary, *, strict: bool = False) -> list[Issue]:
    report = _Report(list(lib.issues), strict)
    _check_criteria_usage(lib, report)
    _check_seed_uniqueness(lib, report)
    _check_catalog(lib, report)
    _check_status_and_references(lib, report)
    return report.issues


def main(argv: Sequence[str] | None = None) -> int:
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        prog="python -m ai.playbooks.lint",
        description="Validate role playbooks, competency skills and the role/level catalog.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="production gate: missing referenced files and draft content are errors",
    )
    parser.add_argument("--playbooks-dir", type=Path, default=PLAYBOOKS_DIR)
    parser.add_argument("--config-dir", type=Path, default=CONFIG_DIR)
    args = parser.parse_args(argv)

    library = load_library(args.playbooks_dir, args.config_dir)
    issues = lint_library(library, strict=args.strict)
    for issue in sorted(issues, key=lambda i: (i.severity != "error", i.path, i.code, i.message)):
        print(issue)

    errors = sum(issue.severity == "error" for issue in issues)
    warnings = len(issues) - errors
    catalog = library.catalog
    role_levels = sum(len(r.levels) for r in catalog.roles.values()) if catalog else 0
    print(
        f"\nScanned {library.files_scanned} playbook file(s): "
        f"{len(library.roles)} role playbook(s), {len(library.skills)} competency skill(s) loaded; "
        f"catalog {'v' + catalog.version if catalog else 'INVALID'} "
        f"({role_levels} role-level configs); "
        f"rubric criteria {'v' + library.criteria.version if library.criteria else 'INVALID'}."
    )
    mode = "strict" if args.strict else "default"
    print(f"{errors} error(s), {warnings} warning(s) [{mode} mode].")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
