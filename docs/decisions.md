# Design decisions

Design decisions that refine the project roadmap. Each entry states the problem,
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
session. Evaluation runs as a FastAPI background task, re-queues `pending`/stale
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

## D14 — Skill library content: converted from the compiled draft library

The first full library was compiled separately (format inspired by DeepInterview, Apache-2.0,
content authored for IntervAI) and converted to this contract:

- per-skill 0–4 criteria (≈50 ids without anchors) → the shared anchored 1–5 criteria of D1; each
  skill keeps its emphasis through weights and per-criterion notes;
- one level per seed → seeds tagged with every level they suit, so each skill has ≥ 2 seeds per
  level (67 seeds in total); every seed gained an `Objective`;
- `Scoring caution` (a common wrong answer not to reward) is kept as an optional seed field and is
  frozen into the plan for the evaluator;
- `communication` / `problem_solving` seeds were redistributed to domain skills (debugging → 
  `programming_fundamentals`, data job sanity → `etl_pipeline`, model latency trade-off →
  `model_evaluation`, release incident → `system_design`), per D3; their rubric ideas became the
  cross-cutting criteria, including the new `hypothesis_testing`;
- the generic "Follow-up Strategies" duplicated in every file moved to the role playbooks'
  `Interviewer Guidance` (it is interviewer behaviour, not skill content).

## D15 — Selection: catalog weights + document boost, D'Hondt allocation bounded by seed capacity

Core skills are always selected. Optional skills are ranked by catalog weight + 0.20 if the JD or
+0.10 if the CV mentions one of the skill's keywords (word-boundary match, reasons recorded and
shown to the user). Documents can add one skill within the mode's budget. Questions are allocated
with D'Hondt (one minimum per skill) and never exceed the skill's seeds at that level; the linter
checks this capacity for every role × level × mode (`catalog-capacity`).

## D16 — The LLM proposes, the playbook decides

The planner LLM returns proposals only. Seed-based questions take expected points, probes and
scoring caution from the seed (the model may rephrase the wording); CV/JD questions must mention a
project/skill from the *validated* analysis and are capped at ⌊main/3⌋ (≥ 1); unknown, duplicate or
surplus proposals are dropped and missing slots filled from unused seeds. Rubric weights always
come from the skill file. CV/JD extraction keeps only projects with a verbatim quote from the CV.

## D17 — PREP never depends on the LLM being available

Without a key, on timeout/quota, or after two invalid outputs, the graph builds the plan from
reviewed seeds (seeded by the session id: varied but reproducible) and records
`planner_model = "deterministic"`; a warning is shown only when documents were provided (their
personalisation is lost). Quota errors never switch to another (paid) model.

## D18 — Guest identity

`POST /api/auth/guest` returns a 256-bit random token once; only its SHA-256 is stored. Every
interview endpoint requires it, and another user's session answers 404, not 403.

## D19 — LIVE: the LLM proposes, backend rules decide

Each answer triggers one structured LLM call (`AnswerDecision`: quality, covered/missing expected
points, `follow_up | clarify | move_on`, question text). `ai/live_rules.py` then enforces:
turns are **reserved for every remaining main question** (so follow-ups never cost core-skill
coverage), at most `max_followups_per_question` follow-ups and one clarification per thread, no
extra turns with < 90 s left, no repeated question text, and only the rules can end an interview
(`plan_completed`, `time_budget`, `max_turns` as a safety net, or the user). When nothing but
`move_on` is allowed, the LLM is not called at all.

## D20 — LIVE degrades gracefully

LLM error/timeout/invalid output → a reviewed follow-up probe from the plan for short answers,
otherwise the next planned question. The interview never stalls on the model. Each answered
turn stores the decision, its source (`llm` / `fallback` / `rules`), latency and prompt version —
never chain-of-thought.

## D21 — One transaction per answer, guarded three ways

`POST /answer` locks the session row (`FOR UPDATE NOWAIT`) for the whole step (record answer → LLM
decision → next turn), so a crash leaves nothing half-written and a concurrent submission gets an
immediate 409. A repeated `request_id` is a no-op (idempotent retry), and a stale `turn_no` is
rejected, so a double click can never answer the next question with the previous text. State is
rebuilt from the database each request, so refresh/restart resumes exactly where it stopped.

## D22 — Turn-based voice: WAV in the browser, Gemini STT, ElevenLabs TTS, text always available

- **Recording:** `MediaRecorder` (any codec the browser has), converted in the browser to 16 kHz
  mono WAV — Gemini does not list WebM as an audio input, every STT accepts WAV, and the backend can
  check the duration from the header (≤ 3 min). The transcript is shown for editing before it is
  sent; the turn records `answer_mode = voice`.
- **STT:** Gemini audio understanding through the same key/gateway as the LLM — no extra vendor.
  The prompt carries a glossary (terms from the current question first, then every playbook
  keyword) and asks for canonical spelling; thinking is disabled for 2.5 Flash. Measured on a test
  clip: terms like LangGraph, BM25, CI/CD transcribed correctly in ~5 s for 15 s of audio (a
  single-skill glossary had produced "LangChain").
- **TTS:** ElevenLabs `eleven_flash_v2_5` (Vietnamese) behind an LRU cache keyed by text. The
  endpoint only speaks questions of the caller's own session (`/turns/{n}/audio`), never arbitrary
  text, to protect credits. Without a key/voice, or on failure, the browser voice reads the
  question.
- **Privacy:** recordings are processed in memory and never stored; only the confirmed transcript
  is persisted.

## D23 — Evaluation: the LLM scores, code verifies and computes

- One call per **question thread** (main question + follow-ups/clarifications), with the frozen
  question, expected points, scoring caution, rubric weights and 1–5 anchors, and the
  turn-numbered transcript. A second call scores cross-cutting skills over the whole transcript;
  a third writes the summary (deterministic fallback if it fails).
- Every score must cite a quote that is found **verbatim** in the cited turn's answer
  (`ai/evaluation/evidence.py`). Invalid quotes are dropped; a criterion left without evidence makes
  the thread invalid → one retry with the problems listed → otherwise `insufficient_evidence`.
  An unbacked score never reaches a report. Cross-cutting criteria without evidence stay empty.
- Weighted/skill/overall scores come from `ai/scoring.py`, using the plan's frozen rubric weights
  and frozen skill weights (`SelectedSkill.weight`), never from the model.
- Jobs: `interview_reports` row created in the transaction that completes the session (only if
  something was answered), claimed with a conditional UPDATE, re-queued on startup when pending or
  stale; failed jobs can be retried and never produce a second report.
- Live smoke test (one synthetic session, gemini-2.5-flash, 3 evaluations of the same transcript):
  per-question scores differed by at most 0.25 on the 1–5 scale; off-topic answers were scored 1
  with the off-topic sentence as evidence. This is a smoke test, not the benchmark.

## D13 — Frontend mocks are contract-tested

With `VITE_API_MODE=mock` the UI runs on in-browser mocks backed by four fixtures (no documents, CV only, JD only,
CV + JD). `tests/unit/test_frontend_fixtures.py` validates them against the Pydantic contracts,
checks every evidence quote is verbatim in the transcript, and recomputes all scores.
