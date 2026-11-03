# Design decisions

Decisions taken at Phase 0 that refine the project roadmap. Each entry states the problem,
the decision, and why. Where this file and the roadmap disagree, this file wins.

## D1 — Rubric anchors are shared and frozen into every plan

**Problem.** Skills declared only weights (`technical_accuracy: 0.40`). An LLM asked for a 1–5
score with no definition of "3" vs "5" scores inconsistently — the roadmap's own top risk.

**Decision.** `ai/config/rubric_criteria.yaml` defines every criterion once with behaviourally
anchored descriptions for all five scores, written *relative to the target level*. Skills choose
criteria + weights (+ an optional skill-specific note) in `## Scoring Rubric`. The planner freezes
the full definitions into `InterviewPlan.rubric_criteria`, so editing the YAML never changes how an
existing session is scored.

**Why.** One scale shared by all skills makes per-skill scores comparable and keeps 14 skill files
free of duplicated anchor text. `completeness` is anchored to the question's expected points, so
it is checkable.

## D2 — Question threads: follow-ups inherit the parent's rubric and are scored together

**Problem.** LIVE follow-ups are generated on the fly and are not in the plan: they had no id,
no expected points and no rubric.

**Decision.** A *question thread* = one planned main question (`q_001`) + its follow-ups
(`q_001.f1`, `q_001.f2`) and clarifications (`q_001.c1`). Non-main turns store
`parent_question_id` and inherit the parent's expected points and rubric. POST evaluates **one
result per thread**, citing evidence from any turn in it.

**Why.** This is how a human interviewer scores: a point the candidate recovers after a probe
still counts. It also gives `answer_evaluations` a natural unique key `(session_id, question_id)`.

## D3 — Communication and problem solving are cross-cutting, not question slots

**Problem.** Treating `communication` / `problem_solving` like other skills would burn one or two
of the three demo questions on soft skills.

**Decision.** Skills declare `assessment: question | cross_cutting`. Cross-cutting skills never
receive question slots; they are scored once over the whole transcript with their own criteria
(`clarity`, `structure`, `decomposition`, `handling_uncertainty`) and reported separately from the
technical overall score. The `clarity` anchors explicitly exclude accent, voice and STT errors.

## D4 — Naming: limits, versions

- `max_followups_per_question` replaces both `max_followups_per_topic` and
  `max_followups_per_skill`: the runaway-follow-up risk is depth on one question.
- `blueprint_version` (left over from v1.2) becomes `catalog_version`; `rubric_version` is added.
  A plan records `plan_schema`, `catalog`, `rubric` and `planner_prompt` versions plus
  `id/version/content_sha256` of every playbook used.
- The LIVE decision is `follow_up | clarify | move_on`. The LLM never proposes `finish`; the backend
  ends the session (plan completed, `max_turns`, time budget, or user).

## D5 — Budgets: main questions vs turns

"5–10 câu" was ambiguous. A mode now fixes both, in `competency_catalog.yaml`:

| Mode | Main questions | Follow-ups / question | Max turns (all kinds) | Time | Skills |
|---|---|---|---|---|---|
| demo | 3 | 1 | 6 | 12 min | 2–3 |
| standard | 6 | 2 | 15 | 30 min | 3–4 |

## D6 — 14 competency skills (adds `programming_fundamentals`)

**Problem.** Backend Intern had only `api_design` and `databases` at its level (`system_design` is
not intern material), but standard mode needs ≥ 3 skills — the catalog could not be satisfied.
Intern/Fresher interviews in practice also test language/OOP/async/testing fundamentals.

**Decision.** Add `competencies/common/programming_fundamentals.md` (used by all three roles at
lower levels). `system_design` targets Fresher/Junior only. Role mapping lives **only** in the
catalog — skill frontmatter has no `roles` field, so there is one source of truth.

## D7 — Report generation: DB-backed job, no queue infrastructure

`interview_reports` holds job state (`status`, `attempts`, `last_error`, timestamps), one row per
session. Phase 4 runs evaluation as a FastAPI background task, re-queues `pending`/stale
`processing` rows on startup (free-tier hosts restart), and relies on unique keys for idempotency.
No Celery/Redis for a single-instance portfolio deploy.

## D8 — Build the library incrementally, gate production with `--strict`

`python -m ai.playbooks.lint` validates everything that exists and reports missing files and
drafts as warnings; `--strict` makes them errors and is the production gate. Content is built as a
vertical slice (AI Engineer + Fresher first) before the remaining files.

## D9 — CV/JD belong to a session

Instead of reusable `profiles` / `job_descriptions` rows with nullable FKs, optional documents are
`session_documents` rows (`UNIQUE(session_id, kind)`, `ON DELETE CASCADE`). Absence means "not
provided" — nothing is fabricated — and deleting a session provably deletes its CV/JD.

## D10 — The client never receives the full plan

`InterviewPlan` contains expected points and rubric notes, i.e. the answers. The API exposes only
`PlanPreview` (skills, counts, time budget, sources, warnings). Expected points appear only in
the report, after the session.

## D11 — Deterministic aggregation

The LLM scores criteria with quoted evidence; numbers are computed in `ai/scoring.py`: question =
Σ weight × score, skill = mean of scored threads, overall = catalog-weighted mean over assessed
skills (insufficient-evidence threads excluded, weights renormalised). Rounded to 2 decimals.

## D12 — Async stack on asyncpg

FastAPI + SQLAlchemy 2 async + asyncpg (psycopg's async mode does not run on Windows' default
event loop). Alembic runs through the same driver. The initial migration is hand-written and CI
verifies it with `alembic check` against the ORM models.

## D13 — Frontend mocks are contract-tested

Phase-0 UI runs on in-browser mocks backed by four fixtures (no documents, CV only, JD only,
CV + JD). `tests/unit/test_frontend_fixtures.py` validates them against the Pydantic contracts,
checks every evidence quote is verbatim in the transcript, and recomputes all scores.
