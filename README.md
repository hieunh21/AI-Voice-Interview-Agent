# IntervAI

**AI voice mock-interview agent for IT roles, in Vietnamese.** Pick a role and a level, optionally
add your CV and/or a job description, and practise a technical interview where the AI asks
adaptive follow-up questions and produces an evidence-linked feedback report.

> Status: **Phase 0 — foundation.** Contracts, database schema, playbook loader/linter, and a
> mock-driven UI are in place. The planner, adaptive interview graph, voice and evaluation land in
> Phases 1–4. Design rationale: [`docs/decisions.md`](docs/decisions.md).

## Scope

- Roles: **AI Engineer, Backend Developer, Data Engineer** × levels **Intern, Fresher, Junior**.
- Role + level are required; **CV and JD are optional** (four input combinations, one planner).
- Turn-based voice (record → STT → agent → TTS) with a text fallback; real-time voice is optional.
- A practice tool — not an official hiring assessment.

## Architecture

```mermaid
flowchart LR
  UI[React + TS] --> API[FastAPI]
  CAT[competency_catalog.yaml] --> SEL[PlaybookSelector<br/>rule-based]
  PB[Role playbooks + competency skills<br/>Markdown + YAML frontmatter] --> SEL
  API --> SEL --> CTX[ContextBuilder<br/>budgeted excerpts] --> PREP[LangGraph planner]
  PREP --> PLAN[(Frozen InterviewPlan<br/>questions, expected points,<br/>rubric + anchors, versions)]
  PLAN --> LIVE[Adaptive interview graph]
  PLAN --> POST[Evaluation + evidence check]
  LIVE --> DB[(PostgreSQL)]
  DB --> POST --> REPORT[Report]
```

**Prep-heavy, live-light.** Playbooks are selected and excerpted once at PREP; the resulting plan
is an immutable snapshot (including rubric anchors and content hashes). LIVE and POST never re-read
the Markdown, so editing a playbook never changes a running or finished session.

## Repository layout

```text
ai/
  config/                 competency_catalog.yaml (role×level→skills), rubric_criteria.yaml (1–5 anchors)
  playbooks/              SCHEMA.md, roles/*.md, competencies/**/*.md, lint.py
  schemas/                Pydantic contracts: setup, plan, decision, evaluation, report
  playbook_loader.py      Markdown/frontmatter → typed playbooks, with collected issues
  scoring.py              deterministic score aggregation
backend/
  app/                    FastAPI app (config, db, api, models, schemas)
  alembic/                migrations
frontend/                 React + TypeScript + Vite + Tailwind
tests/                    unit + integration (migrations) tests
deploy/                   Dockerfiles
docs/                     design decisions
eval/                     benchmark datasets & A/B runner (Phase 6)
```

## Quick start

Prerequisites: [uv](https://docs.astral.sh/uv/), Node.js 22+, Docker.

```bash
cp .env.example .env
docker compose up -d db                              # PostgreSQL 17
uv sync                                              # Python 3.12 deps
uv run alembic -c backend/alembic.ini upgrade head   # create schema
uv run uvicorn app.main:create_app --factory --reload   # API on http://localhost:8000

cd frontend
npm install
npm run dev                                          # UI on http://localhost:5173
```

Or run PostgreSQL + backend together with `docker compose up --build`.

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Liveness + version |
| `GET /api/health/ready` | Readiness (database reachable) |
| `GET /docs` | OpenAPI UI (disabled in production) |

## Quality checks

```bash
uv run ruff check . && uv run ruff format --check .
uv run python -m ai.playbooks.lint          # add --strict for the production gate
uv run pytest                                # DB tests need TEST_DATABASE_URL
cd frontend && npm run lint && npm run test && npm run build
```

Migration tests run against a disposable database:

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
- **Competency skills** (14) — *what* to ask and score: core knowledge, question seeds with
  expected points and follow-up probes, rubric weights, references.
- **Rubric criteria** — shared 1–5 anchors, frozen into each plan.

The file contract is in [`ai/playbooks/SCHEMA.md`](ai/playbooks/SCHEMA.md). Only
`status: reviewed` content is allowed in production.

## Evaluation (planned, Phase 6)

An A/B study compares plan and follow-up quality **with vs. without playbook context** on held-out
scenarios, alongside WER, latency and evidence-validity metrics. No numbers are reported until
they are measured.
