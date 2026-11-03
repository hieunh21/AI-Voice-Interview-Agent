# Playbook Library — File Contract

This document is the contract enforced by `python -m ai.playbooks.lint`. Playbooks are
**application data reviewed like code**: they are not user-uploadable, not generated from user
transcripts, and not a vector store.

```text
ai/
├── config/
│   ├── competency_catalog.yaml   # role × level → skills, weights, core flags, mode limits
│   └── rubric_criteria.yaml      # shared criteria with anchored 1–5 scales
└── playbooks/
    ├── SCHEMA.md                 # this file
    ├── roles/<role>.md           # 3 role playbooks — HOW to run the interview
    └── competencies/<group>/<skill_id>.md   # competency skills — WHAT to ask and how to score
```

## Ownership rules

| Concern | Lives in | Never in |
|---|---|---|
| Which skills a role-level uses, weights, core flags | `competency_catalog.yaml` | skill frontmatter |
| Score anchors (what 1…5 means) | `rubric_criteria.yaml` | skill files |
| Criteria + weights per skill, skill-specific scoring notes | skill `## Scoring Rubric` | catalog |
| Questions, expected points, follow-up probes | skill `## Question Seeds` | role playbooks |
| Round structure, interviewer behaviour, level strategy | role playbook | skill files |

Everything the planner needs must be written **in the Markdown itself**. URLs under
`## References` exist to fact-check the content; they never replace it.

## Common rules

- UTF-8, LF line endings, starts with a `---` YAML frontmatter block.
- Exactly one `# Title` heading. Sections are `## Heading` with the **exact** names below.
  Unknown sections produce a warning. Headings inside fenced code blocks are ignored.
- `version` is semver (`1.0.0`). Bump it whenever expected points, seeds or rubric change
  (patch: wording; minor: new seed/probe; major: changed scoring or removed seed). Add a line to
  `## Changelog`.
- `status`: `draft` → `reviewed` → `deprecated`. Only `reviewed` content may reach production
  (`ALLOW_DRAFT_PLAYBOOKS=false`, and `lint --strict` fails on drafts).
- Levels are `intern`, `fresher`, `junior`. Level headings are written `### Intern`,
  `### Fresher`, `### Junior` (case-insensitive).

## Role playbook — `roles/<role>.md`

```yaml
---
id: role_ai_engineer        # must be role_<role>; file name must be <role>.md
kind: role_playbook
version: 1.0.0
role: ai_engineer           # ai_engineer | backend_developer | data_engineer
levels: [intern, fresher, junior]   # must cover all three
status: draft
---
```

| Section | Required | Content |
|---|---|---|
| `## Round Structure` | yes | Phases of the interview and how questions are ordered |
| `## Level Guidance` | yes | One `### <Level>` subsection per level: depth, question types, what not to expect |
| `## Positive Signals` | yes | Bullets: what a strong answer looks like for this role |
| `## Pitfalls` | yes | Bullets: common mistakes to probe |
| `## Interviewer Guidance` | yes | Bullets: how to ask, follow up and move on |
| `## Purpose` | no | One paragraph: what this interview assesses |
| `## Interviewer Probes` | no | Bullets: generic probes the planner may adapt |
| `## References`, `## Changelog`, `## Notes` | no | |

## Competency skill — `competencies/<group>/<skill_id>.md`

```yaml
---
id: rag_systems             # unique; file name must be <id>.md; must not start with role_
kind: competency_skill
version: 1.0.0
assessment: question        # question (gets question slots) | cross_cutting (scored over all answers)
levels: [intern, fresher, junior]
keywords: [rag, retrieval, embedding]   # lower-cased; used to match CV/JD content
status: draft
---
```

Role mapping is **not** declared here — `competency_catalog.yaml` is the single source of truth.

| Section | `question` | `cross_cutting` | Content |
|---|---|---|---|
| `## Learning Objectives` | required | required | Bullets: what the skill assesses |
| `## Core Knowledge` | required | optional | Reviewed technical summary in your own words |
| `## Level Guidance` | required | required | `### <Level>` per frontmatter level |
| `## Question Seeds` | required | — | See below |
| `## Scoring Rubric` | required | required | See below |
| `## Positive Signals` | required | required | Bullets |
| `## Pitfalls` | required | required | Bullets |
| `## References` | required | optional | Bullets, each with a URL to a trustworthy source |
| `## Changelog`, `## Notes` | optional | optional | |

### Question seeds

Each seed is a `###` subsection. The heading is `<seed_id> — <question text>` (`—`, `–` or `-`).
Seed ids are unique across the whole library.

```markdown
### rag_hybrid_01 — Khi nào nên dùng hybrid retrieval?
**Levels:** fresher, junior
**Objective:** Hiểu trade-off dense/sparse/hybrid và cách chứng minh cải tiến.
**Expected points:**
- Dense mạnh về ngữ nghĩa; sparse (BM25) mạnh với từ khóa chính xác.
- Kết hợp bằng Reciprocal Rank Fusion hoặc chuẩn hóa điểm.
**Follow-up probes:**
- Vì sao không cộng trực tiếp điểm cosine và điểm BM25?
**Scoring caution:** Không coi việc nối hai danh sách mà không khử trùng lặp là fusion đúng.
```

- `Levels`, `Objective`, `Expected points` and `Follow-up probes` are required; `Scoring caution`
  (a common wrong answer the evaluator must not reward) is optional and frozen into the plan.
  `Levels` must be a subset of the skill's levels.
- `Expected points`: ≥ 2 bullets, each a checkable idea (scored by `completeness`).
- `Follow-up probes`: ≥ 1 bullet. They are *hints*; LIVE follow-ups must still react to the
  candidate's actual answer.
- Every skill level needs ≥ 1 seed (error); fewer than 2 per level is a warning.

### Scoring rubric

```markdown
## Scoring Rubric
- technical_accuracy: 0.40 — Không nhầm retrieval metric với chất lượng câu trả lời.
- completeness: 0.25
- reasoning: 0.20 — Nêu trade-off chất lượng, latency, chi phí.
- practical_examples: 0.15
```

- Criterion ids must exist in `ai/config/rubric_criteria.yaml` and match the skill's
  `assessment` (`applies_to`). Weights must sum to 1.0.
- The text after `—` is a skill-specific note for the evaluator; the 1–5 anchors themselves are
  shared and live in `rubric_criteria.yaml`.

## How the library is used at runtime

1. **PREP** — `PlaybookSelector` (Python, no LLM) picks 1 role playbook + 2–4 skills from the
   catalog for the role/level/mode, boosting optional skills that match CV/JD keywords.
   `ContextBuilder` extracts only the needed sections for the target level within a budget.
   The LLM planner writes the `InterviewPlan`, which freezes questions, expected points,
   follow-up hints, rubric weights, criterion anchors and every `id/version/content_sha256`.
2. **LIVE** — reads only the frozen plan + recent turns. Markdown is never re-read.
3. **POST** — scores each question thread with the frozen rubric; changing a file later never
   changes an existing session's scoring.

## Provenance

The Markdown + YAML-frontmatter playbook mechanism (metadata-based selection, bounded excerpts
for the planner) is inspired by the public
[DeepInterview skill library](https://github.com/ngoanpv/DeepInterview/tree/main/skills)
(Apache-2.0). IntervAI's two-kind schema, shared anchored rubric and all questions, expected
points and rubric notes are authored for IntervAI; no playbook content is copied.

## Lint

```bash
uv run python -m ai.playbooks.lint            # incremental: missing files / drafts are warnings
uv run python -m ai.playbooks.lint --strict   # production gate: they are errors
```
