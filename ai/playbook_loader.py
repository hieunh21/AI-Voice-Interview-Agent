"""Load the Playbook Library (Markdown + YAML frontmatter) and YAML configs into typed contracts.

The loader validates each file on its own (frontmatter schema, required sections, level guidance,
question seeds, rubric syntax) and collects every problem as an `Issue` instead of stopping at the
first one. Cross-file rules (catalog references, criteria, uniqueness, review status) live in
`ai.playbooks.lint`. The section contract is documented in `ai/playbooks/SCHEMA.md`.
"""

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ValidationError

from ai import CONFIG_DIR, PLAYBOOKS_DIR
from ai.markdown import (
    FrontmatterError,
    parse_bullets,
    parse_fields,
    split_frontmatter,
    split_sections,
)
from ai.schemas.catalog import CompetencyCatalog, RubricCriteriaCatalog
from ai.schemas.common import check_rubric_weights
from ai.schemas.enums import Assessment, Level
from ai.schemas.playbook import (
    CompetencySkill,
    CompetencySkillMeta,
    QuestionSeed,
    RolePlaybook,
    RolePlaybookMeta,
    RubricCriterion,
)

CATALOG_FILE = "competency_catalog.yaml"
CRITERIA_FILE = "rubric_criteria.yaml"
ROLES_SUBDIR = "roles"
COMPETENCIES_SUBDIR = "competencies"

ROLE_REQUIRED_SECTIONS = (
    "Round Structure",
    "Level Guidance",
    "Positive Signals",
    "Pitfalls",
    "Interviewer Guidance",
)
ROLE_OPTIONAL_SECTIONS = ("Purpose", "Interviewer Probes", "References", "Changelog", "Notes")

SKILL_REQUIRED_SECTIONS: dict[Assessment, tuple[str, ...]] = {
    Assessment.QUESTION: (
        "Learning Objectives",
        "Core Knowledge",
        "Level Guidance",
        "Question Seeds",
        "Scoring Rubric",
        "Positive Signals",
        "Pitfalls",
        "References",
    ),
    Assessment.CROSS_CUTTING: (
        "Learning Objectives",
        "Level Guidance",
        "Scoring Rubric",
        "Positive Signals",
        "Pitfalls",
    ),
}
SKILL_OPTIONAL_SECTIONS: dict[Assessment, tuple[str, ...]] = {
    Assessment.QUESTION: ("Changelog", "Notes"),
    Assessment.CROSS_CUTTING: ("Core Knowledge", "References", "Changelog", "Notes"),
}

SEED_FIELDS = ("levels", "objective", "expected points", "follow-up probes")
SEED_OPTIONAL_FIELDS = ("scoring caution",)

_SEED_HEADING_RE = re.compile(r"^(?P<id>[a-z][a-z0-9_]{1,63})\s+[—–-]\s+(?P<question>\S.*)$")
_RUBRIC_LINE_RE = re.compile(
    r"^(?P<id>[a-z][a-z0-9_]*)\s*:\s*(?P<weight>\d*\.?\d+)\s*(?:[—–-]\s*(?P<note>.*))?$"
)

Severity = Literal["error", "warning"]


@dataclass(frozen=True)
class Issue:
    severity: Severity
    code: str
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.severity} [{self.code}] {self.message}"


@dataclass
class PlaybookLibrary:
    catalog: CompetencyCatalog | None
    criteria: RubricCriteriaCatalog | None
    catalog_path: str
    criteria_path: str
    roles: dict[str, RolePlaybook] = field(default_factory=dict)
    skills: dict[str, CompetencySkill] = field(default_factory=dict)
    issues: list[Issue] = field(default_factory=list)
    files_scanned: int = 0


class _Issues:
    """Issue collector bound to one file."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.items: list[Issue] = []

    def error(self, code: str, message: str) -> None:
        self.items.append(Issue("error", code, self.path, message))

    def warn(self, code: str, message: str) -> None:
        self.items.append(Issue("warning", code, self.path, message))

    def validation(self, code: str, exc: ValidationError, prefix: str = "") -> None:
        for err in exc.errors():
            loc = ".".join(str(part) for part in err["loc"])
            where = f"{prefix}{loc}" if loc else prefix.rstrip(": ") or "value"
            self.error(code, f"{where}: {err['msg']}")

    @property
    def has_errors(self) -> bool:
        return any(issue.severity == "error" for issue in self.items)


def display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


@dataclass(frozen=True)
class _Document:
    frontmatter: dict[str, object]
    title: str
    sections: dict[str, str]
    content_sha256: str


def _read_document(path: Path, out: _Issues) -> _Document | None:
    try:
        text = path.read_bytes().decode("utf-8").replace("\r\n", "\n")
    except UnicodeDecodeError:
        out.error("encoding", "file must be UTF-8 encoded")
        return None
    try:
        frontmatter, body = split_frontmatter(text)
    except FrontmatterError as exc:
        out.error("frontmatter", str(exc))
        return None

    preamble, titles = split_sections(body, 1)
    if len(titles) != 1:
        out.error("title", f"expected exactly one '# Title' heading, found {len(titles)}")
        return None
    if preamble:
        out.warn("stray-content", "content before the '# Title' heading is ignored")

    _, h2_sections = split_sections(titles[0].body, 2)
    sections: dict[str, str] = {}
    for section in h2_sections:
        if section.title in sections:
            out.error("duplicate-section", f"section '## {section.title}' appears more than once")
            continue
        sections[section.title] = section.body
    return _Document(
        frontmatter=frontmatter,
        title=titles[0].title,
        sections=sections,
        content_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
    )


def _check_sections(
    sections: dict[str, str],
    required: tuple[str, ...],
    optional: tuple[str, ...],
    out: _Issues,
) -> None:
    for name in required:
        if name not in sections:
            out.error("missing-section", f"missing required section '## {name}'")
        elif not sections[name].strip():
            out.error("empty-section", f"section '## {name}' is empty")
    allowed = set(required) | set(optional)
    for name in sections:
        if name not in allowed:
            out.warn("unknown-section", f"section '## {name}' is not in the contract (SCHEMA.md)")


def _parse_level_guidance(body: str, levels: list[Level], out: _Issues) -> dict[Level, str]:
    _, subsections = split_sections(body, 3)
    found: dict[Level, str] = {}
    for sub in subsections:
        try:
            level = Level(sub.title.strip().lower())
        except ValueError:
            out.error(
                "level-guidance",
                f"unknown heading '### {sub.title}' under Level Guidance "
                f"(expected one of: {', '.join(lv.value.capitalize() for lv in Level)})",
            )
            continue
        if level in found:
            out.error("level-guidance", f"'### {sub.title}' appears more than once")
            continue
        if not sub.body.strip():
            out.error("level-guidance", f"'### {sub.title}' is empty")
        if level not in levels:
            out.warn("level-guidance", f"'### {sub.title}' is not listed in frontmatter levels")
        found[level] = sub.body
    for level in levels:
        if level not in found:
            out.error(
                "level-guidance",
                f"missing '### {level.value.capitalize()}' under '## Level Guidance'",
            )
    return found


def _parse_seeds(body: str, skill_levels: list[Level], out: _Issues) -> list[QuestionSeed]:
    _, subsections = split_sections(body, 3)
    seeds: list[QuestionSeed] = []
    seen: set[str] = set()
    for sub in subsections:
        heading = _SEED_HEADING_RE.match(sub.title)
        if heading is None:
            out.error(
                "seed-heading",
                f"'### {sub.title}' must look like '### <seed_id> — <question text>'",
            )
            continue
        seed_id = heading.group("id")
        if seed_id in seen:
            out.error("duplicate-seed", f"seed id '{seed_id}' is used twice in this file")
            continue
        seen.add(seed_id)

        fields, duplicates = parse_fields(sub.body)
        for label in duplicates:
            out.error("seed-field", f"{seed_id}: field '**{label}:**' appears more than once")
        for label in sorted(set(fields) - set(SEED_FIELDS) - set(SEED_OPTIONAL_FIELDS)):
            out.error("seed-field", f"{seed_id}: unknown field '**{label}:**'")
        missing = [label for label in SEED_FIELDS if not fields.get(label)]
        for label in missing:
            out.error("seed-field", f"{seed_id}: missing or empty field '**{label}:**'")
        if missing:
            continue

        data = {
            "id": seed_id,
            "question": heading.group("question").strip(),
            "levels": [p.strip().lower() for p in fields["levels"].split(",") if p.strip()],
            "objective": " ".join(fields["objective"].split()),
            "expected_points": parse_bullets(fields["expected points"]),
            "followup_probes": parse_bullets(fields["follow-up probes"]),
            "scoring_caution": " ".join(fields.get("scoring caution", "").split()) or None,
        }
        try:
            seed = QuestionSeed.model_validate(data)
        except ValidationError as exc:
            out.validation("seed-invalid", exc, prefix=f"{seed_id}: ")
            continue
        outside = [lv.value for lv in seed.levels if lv not in skill_levels]
        if outside:
            out.error("seed-levels", f"{seed_id}: levels {outside} are not in frontmatter levels")
            continue
        seeds.append(seed)

    if not subsections:
        out.error("seed-heading", "'## Question Seeds' contains no '### <seed_id> — ...' entries")
    for level in skill_levels:
        count = sum(level in seed.levels for seed in seeds)
        if count == 0:
            out.error("seed-coverage", f"no question seed covers level '{level.value}'")
        elif count == 1:
            out.warn(
                "seed-coverage",
                f"only one seed covers level '{level.value}'; add another so plans can vary",
            )
    return seeds


def _parse_rubric(body: str, out: _Issues) -> list[RubricCriterion]:
    items = parse_bullets(body)
    if not items:
        out.error("rubric", "list criteria as '- <criterion_id>: <weight> — <note>' bullets")
        return []
    rubric: list[RubricCriterion] = []
    for item in items:
        match = _RUBRIC_LINE_RE.match(item)
        if match is None:
            out.error("rubric", f"cannot parse rubric line '- {item}'")
            continue
        try:
            rubric.append(
                RubricCriterion(
                    criterion_id=match.group("id"),
                    weight=float(match.group("weight")),
                    note=(match.group("note") or "").strip() or None,
                )
            )
        except ValidationError as exc:
            out.validation("rubric", exc, prefix=f"{match.group('id')}: ")
    if rubric:
        try:
            check_rubric_weights(rubric)
        except ValueError as exc:
            out.error("rubric-weights", str(exc))
    return rubric


def load_role_playbook(path: Path) -> tuple[RolePlaybook | None, list[Issue]]:
    out = _Issues(display_path(path))
    doc = _read_document(path, out)
    if doc is None:
        return None, out.items
    try:
        meta = RolePlaybookMeta.model_validate(doc.frontmatter)
    except ValidationError as exc:
        out.validation("frontmatter-schema", exc)
        return None, out.items

    if path.stem != meta.role.value or meta.id != f"role_{meta.role.value}":
        out.error(
            "file-name",
            f"role playbook for '{meta.role.value}' must be roles/{meta.role.value}.md "
            f"with id 'role_{meta.role.value}'",
        )
    _check_sections(doc.sections, ROLE_REQUIRED_SECTIONS, ROLE_OPTIONAL_SECTIONS, out)
    level_guidance = _parse_level_guidance(doc.sections.get("Level Guidance", ""), meta.levels, out)

    if out.has_errors:
        return None, out.items
    playbook = RolePlaybook(
        meta=meta,
        title=doc.title,
        sections=doc.sections,
        level_guidance=level_guidance,
        path=out.path,
        content_sha256=doc.content_sha256,
    )
    return playbook, out.items


def load_competency_skill(path: Path) -> tuple[CompetencySkill | None, list[Issue]]:
    out = _Issues(display_path(path))
    doc = _read_document(path, out)
    if doc is None:
        return None, out.items
    try:
        meta = CompetencySkillMeta.model_validate(doc.frontmatter)
    except ValidationError as exc:
        out.validation("frontmatter-schema", exc)
        return None, out.items

    if path.stem != meta.id:
        out.error("file-name", f"skill '{meta.id}' must live in a file named {meta.id}.md")
    if meta.id.startswith("role_"):
        out.error("frontmatter-schema", "id: competency skill ids must not start with 'role_'")

    _check_sections(
        doc.sections,
        SKILL_REQUIRED_SECTIONS[meta.assessment],
        SKILL_OPTIONAL_SECTIONS[meta.assessment],
        out,
    )
    level_guidance = _parse_level_guidance(doc.sections.get("Level Guidance", ""), meta.levels, out)
    seeds: list[QuestionSeed] = []
    if meta.assessment is Assessment.QUESTION and "Question Seeds" in doc.sections:
        seeds = _parse_seeds(doc.sections["Question Seeds"], meta.levels, out)
    rubric = _parse_rubric(doc.sections.get("Scoring Rubric", ""), out)
    references = parse_bullets(doc.sections.get("References", ""))

    if out.has_errors:
        return None, out.items
    skill = CompetencySkill(
        meta=meta,
        title=doc.title,
        sections=doc.sections,
        level_guidance=level_guidance,
        seeds=seeds,
        rubric=rubric,
        references=references,
        path=out.path,
        content_sha256=doc.content_sha256,
    )
    return skill, out.items


def _load_yaml_config[M: BaseModel](path: Path, model: type[M], issues: list[Issue]) -> M | None:
    out = _Issues(display_path(path))
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        out.error("missing-file", "config file not found")
        data = None
    except yaml.YAMLError as exc:
        out.error("yaml", f"invalid YAML: {exc}")
        data = None
    result: M | None = None
    if data is not None or not out.has_errors:
        try:
            result = model.model_validate(data)
        except ValidationError as exc:
            out.validation("config-schema", exc)
    issues.extend(out.items)
    return result


def load_library(
    playbooks_dir: Path = PLAYBOOKS_DIR, config_dir: Path = CONFIG_DIR
) -> PlaybookLibrary:
    issues: list[Issue] = []
    catalog_path = config_dir / CATALOG_FILE
    criteria_path = config_dir / CRITERIA_FILE
    library = PlaybookLibrary(
        catalog=_load_yaml_config(catalog_path, CompetencyCatalog, issues),
        criteria=_load_yaml_config(criteria_path, RubricCriteriaCatalog, issues),
        catalog_path=display_path(catalog_path),
        criteria_path=display_path(criteria_path),
        issues=issues,
    )

    for path in sorted((playbooks_dir / ROLES_SUBDIR).glob("*.md")):
        library.files_scanned += 1
        playbook, file_issues = load_role_playbook(path)
        library.issues.extend(file_issues)
        if playbook is None:
            continue
        if playbook.meta.id in library.roles:
            library.issues.append(
                Issue("error", "duplicate-id", playbook.path, f"id '{playbook.meta.id}' is reused")
            )
            continue
        library.roles[playbook.meta.id] = playbook

    for path in sorted((playbooks_dir / COMPETENCIES_SUBDIR).rglob("*.md")):
        library.files_scanned += 1
        skill, file_issues = load_competency_skill(path)
        library.issues.extend(file_issues)
        if skill is None:
            continue
        if skill.meta.id in library.skills:
            other = library.skills[skill.meta.id].path
            library.issues.append(
                Issue("error", "duplicate-id", skill.path, f"id '{skill.meta.id}' also in {other}")
            )
            continue
        library.skills[skill.meta.id] = skill

    return library
