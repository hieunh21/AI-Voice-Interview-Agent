# IntervAI

**AI voice mock-interview agent for IT roles, in Vietnamese.** Pick a role and a level, optionally
add your CV and/or a job description, and practise a technical interview where the AI asks
adaptive follow-up questions and produces an evidence-linked feedback report.

> **Status.** Working today: guest sessions, optional CV/JD (paste, TXT or PDF), rule-based
> playbook selection, a LangGraph planner (Gemini, with a seed-only fallback) that produces a
> frozen, versioned interview plan, and an adaptive **text** interview: a LangGraph interviewer
> that follows up on what the candidate actually said, within backend-enforced limits, with
> idempotent answers and resume after refresh — by text or **turn-based voice** (record → editable
> transcript via Gemini → questions read aloud by ElevenLabs or the browser voice) — and an
> **evidence-based report**: every score cites verified quotes from the transcript, scored against
> the frozen rubric, aggregated deterministically. Next: benchmark, A/B study and deployment.
> Design rationale: [`docs/decisions.md`](docs/decisions.md).

## Scope

- Roles: **AI Engineer, Backend Developer, Data Engineer** × levels **Intern, Fresher, Junior**.
- Role + level are required; **CV and JD are optional** (four input combinations, one planner).
- Turn-based voice (record → STT → agent → TTS) with a text fallback; real-time voice is optional.
- A practice tool — not an official hiring assessment.

## Architecture

```mermaid
flowchart LR
  UI[React + TS] --> API[FastAPI]
  API --> DOC[CV/JD analysis<br/>LLM + verbatim evidence check]
  CAT[competency_catalog.yaml] --> SEL[PlaybookSelector<br/>rule-based]
  PB[Role playbooks + competency skills<br/>Markdown + YAML frontmatter] --> SEL
  DOC --> SEL --> CTX[ContextBuilder<br/>budgeted excerpts] --> PREP[LangGraph planner<br/>LLM proposes, code validates]
  PREP --> PLAN[(Frozen InterviewPlan<br/>questions, expected points,<br/>rubric + anchors, versions)]
  PLAN --> LIVE[Adaptive interview graph]
  PLAN --> POST[Evaluation + evidence check]
  LIVE --> DB[(PostgreSQL)]
  DB --> POST --> REPORT[Report]
```

**Prep-heavy, live-light.** Playbooks are selected and excerpted once at PREP; the resulting plan
is an immutable snapshot (including rubric anchors and content hashes). LIVE and POST never re-read
the Markdown, so editing a playbook never changes a running or finished session.

**The LLM proposes, the playbook decides.** The planner may rephrase reviewed questions or add a
CV/JD-grounded question, but expected points, rubric weights and scoring cautions always come from
the reviewed skill files. If the LLM is unavailable, plans are built from the reviewed seeds.

## Repository layout

```text
ai/
  config/                 competency_catalog.yaml (role×level→skills), rubric_criteria.yaml (1–5 anchors)
  playbooks/              SCHEMA.md, roles/*.md (3), competencies/**/*.md (14), lint.py
  schemas/                Pydantic contracts: setup, plan, documents, decision, evaluation, report
  playbook_loader.py      Markdown/frontmatter → typed playbooks, with collected issues
  playbook_selector.py    rule-based skill selection + question allocation
  context_builder.py      bounded, level-specific planner context
  documents.py            PDF/TXT text extraction
  nodes/                  CV/JD analysis, planner validation/assembly
  graphs/prep_graph.py    LangGraph PREP graph
  graphs/interview_graph.py  LangGraph LIVE graph (answer analysis → rules → next turn)
  live_rules.py           backend-enforced interview limits
  llm/                    structured-output LLM interface, Gemini adapter, fake
  prompts/                versioned prompts
  evaluation/             evaluator (per thread, cross-cutting, summary) + evidence checker
  scoring.py              deterministic score aggregation
speech/                   STT (Gemini) / TTS (ElevenLabs + cache) adapters, audio validation
backend/
  app/                    FastAPI app (config, runtime, api, services, models, schemas)
  alembic/                migrations
frontend/                 React + TypeScript + Vite + Tailwind
tests/                    unit + integration (PostgreSQL) tests
deploy/                   Dockerfiles
docs/                     design decisions
eval/                     benchmark datasets & A/B runner
```

## Quick start

Prerequisites: [uv](https://docs.astral.sh/uv/), Node.js 22+, Docker.

```bash
cp .env.example .env            # optionally set GEMINI_API_KEY (https://aistudio.google.com)
docker compose up -d db                              # PostgreSQL 17
uv sync                                              # Python 3.12 deps
uv run alembic -c backend/alembic.ini upgrade head   # create schema
uv run uvicorn app.main:create_app --factory --reload   # API on http://localhost:8000

cd frontend
npm install
npm run dev                                          # UI on http://localhost:5173
```

Or run PostgreSQL + backend together with `docker compose up --build`. Without `GEMINI_API_KEY`
the app still works: plans are built from the reviewed question seeds, without CV/JD analysis.
`GEMINI_MODEL` selects the model (e.g. `gemini-2.5-flash`); `GEMINI_BASE_URL` routes requests
through a Gemini-compatible gateway — CV/JD text is then processed by that provider as well.
Voice: speech-to-text reuses the Gemini settings; set `ELEVENLABS_API_KEY` and
`ELEVENLABS_VOICE_ID` to read questions with ElevenLabs (otherwise the browser voice is used).
Set `VITE_API_MODE=mock` in `frontend/.env.local` to run the UI without a backend.

| Endpoint | Purpose |
|---|---|
| `GET /api/health`, `GET /api/health/ready` | Liveness + version / database readiness |
| `POST /api/auth/guest` | Create a guest identity (bearer token, returned once) |
| `POST /api/interviews` | Create a session: `role`, `level` required; `mode`, `cv_text`, `jd_text` optional |
| `POST /api/interviews/{id}/cv`, `/jd` | Upload an optional CV / JD (PDF with text layer, or TXT) |
| `POST /api/interviews/{id}/prepare` | Build and freeze the interview plan (idempotent) |
| `POST /api/interviews/{id}/start` | Start a prepared session; returns the first question (idempotent) |
| `POST /api/interviews/{id}/answer` | `{request_id, turn_no, answer_text}` → follow-up, next question or end |
| `POST /api/interviews/{id}/finish` | End early; answered turns are kept and evaluated (idempotent) |
| `GET /api/interviews/{id}/report` | Report status (`pending/processing/completed/failed`) and the report |
| `POST /api/interviews/{id}/report/retry` | Re-run a failed evaluation (never creates a second report) |
| `POST /api/interviews/{id}/transcribe` | Recorded answer (WAV ≤ 3 min) → editable transcript; audio is not stored |
| `GET /api/interviews/{id}/turns/{n}/audio` | Question `n` read aloud (audio/mpeg); only this session's questions |
| `GET /api/speech/capabilities` | Which voice features are configured (UI falls back to text / browser voice) |
| `GET /api/interviews`, `GET /api/interviews/{id}` | List sessions / session with plan preview and turns |
| `DELETE /api/interviews/{id}` | Delete a session with its documents, plan and transcript |
| `GET /docs` | OpenAPI UI (disabled in production) |

The client only ever receives a plan *preview* (topics, counts, time budget, why each skill was
chosen) — never the expected points, which would reveal the answers.

## Quality checks

```bash
uv run ruff check . && uv run ruff format --check .
uv run python -m ai.playbooks.lint          # add --strict for the production gate
uv run pytest                                # DB tests need TEST_DATABASE_URL
cd frontend && npm run lint && npm run test && npm run build
```

Integration tests (migrations and the API) run against a disposable database:

```bash
docker exec intervai-db-1 psql -U intervai -c "CREATE DATABASE intervai_test;"
TEST_DATABASE_URL=postgresql://intervai:intervai@localhost:5432/intervai_test uv run pytest tests/integration
```

CI (`.github/workflows/ci.yml`) runs all of the above, including `alembic check` to prove the
migrations match the ORM models.

## Playbook Library

Interview knowledge is versioned Markdown reviewed like code — no vector database:

- **Catalog** — 9 role/level configs: skills, weights, core flags, mode limits.
- **Role playbooks** (3) — *how* to run the interview: round structure, level strategy, signals.
- **Competency skills** (14) — *what* to ask and score: core knowledge, 67 question seeds with
  expected points, follow-up probes and scoring cautions, rubric weights, references.
- **Rubric criteria** — shared 1–5 anchors, frozen into each plan.

The file contract is in [`ai/playbooks/SCHEMA.md`](ai/playbooks/SCHEMA.md). Only
`status: reviewed` content is allowed in production (`ALLOW_DRAFT_PLAYBOOKS=false`).

## Evaluation (planned)

An A/B study will compare plan and follow-up quality **with vs. without playbook context** on
held-out scenarios, alongside WER, latency and evidence-validity metrics. No numbers are reported
until they are measured.
