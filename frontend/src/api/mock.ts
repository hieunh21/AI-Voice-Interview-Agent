import cvJd from '../mocks/fixtures/cv_jd.json'
import cvOnly from '../mocks/fixtures/cv_only.json'
import jdOnly from '../mocks/fixtures/jd_only.json'
import noDocs from '../mocks/fixtures/no_docs.json'
import { CV_OPENING_QUESTION, QUESTION_BANK, SKILL_TITLES, type MockQuestion } from '../mocks/questionBank'
import {
  ApiError,
  type AnswerSubmission,
  type ApiClient,
  type CriterionScore,
  type EndReason,
  type EvaluationResult,
  type InputSource,
  type InterviewMode,
  type InterviewReport,
  type InterviewSetup,
  type PlanPreview,
  type ReportResponse,
  type SessionSummary,
  type SessionView,
  type TurnView,
} from './types'

/**
 * In-browser stand-in for the backend (VITE_API_MODE=mock). It follows the backend's rules:
 * limits from the catalog, at most N follow-ups per question, idempotent answers,
 * and reports only after the session ends. Scores here are placeholders, not AI evaluation.
 */

interface Fixture {
  session: SessionView
  report: InterviewReport | null
}

interface MockRecord {
  session: SessionView
  report: InterviewReport | null
  script: MockQuestion[]
  processedRequests: string[]
}

const STORAGE_KEY = 'intervai.mock.v1'
const LATENCY_MS = 300

// Mirrors ai/config/competency_catalog.yaml (modes).
const LIMITS: Record<InterviewMode, { main: number; followUps: number; maxTurns: number; minutes: number }> = {
  demo: { main: 3, followUps: 1, maxTurns: 6, minutes: 12 },
  standard: { main: 6, followUps: 2, maxTurns: 15, minutes: 30 },
}
const SHORT_ANSWER_CHARS = 220
const STANDARD_WEIGHTS: Record<string, number> = {
  technical_accuracy: 0.4,
  completeness: 0.25,
  reasoning: 0.2,
  practical_examples: 0.15,
}

const FIXTURES = [noDocs, cvOnly, jdOnly, cvJd] as unknown as Fixture[]

const delay = (ms = LATENCY_MS) => new Promise((resolve) => setTimeout(resolve, ms))
const now = () => new Date().toISOString()
const round2 = (value: number) => Math.round(value * 100) / 100
const clampScore = (value: number) => Math.min(5, Math.max(1, Math.round(value)))

function scriptFor(session: SessionView, hasCv: boolean): MockQuestion[] {
  const questions = QUESTION_BANK[session.role].slice(0, LIMITS[session.mode].main)
  const first = questions[0]
  if (hasCv && first) questions[0] = { ...first, text: CV_OPENING_QUESTION }
  return questions
}

function seedRecords(): Map<string, MockRecord> {
  const records = new Map<string, MockRecord>()
  for (const fixture of FIXTURES) {
    const session = structuredClone(fixture.session)
    records.set(session.id, {
      session,
      report: structuredClone(fixture.report),
      script: QUESTION_BANK[session.role].slice(0, LIMITS[session.mode].main),
      processedRequests: [],
    })
  }
  return records
}

function loadRecords(): Map<string, MockRecord> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return new Map(JSON.parse(raw) as [string, MockRecord][])
  } catch {
    // Storage unavailable or corrupted: fall back to the fixtures.
  }
  return seedRecords()
}

function previewFor(
  setup: InterviewSetup,
  script: MockQuestion[],
  docs: { cv: boolean; jd: boolean },
): PlanPreview {
  const counts = new Map<string, number>()
  for (const q of script) counts.set(q.skillId, (counts.get(q.skillId) ?? 0) + 1)
  const sources: InputSource[] = ['role_config', 'role_playbook', 'competency_skills']
  if (docs.cv) sources.push('cv')
  if (docs.jd) sources.push('jd')
  const limits = LIMITS[setup.mode]
  return {
    role_playbook: { id: `role_${setup.role}`, version: '1.0.0' },
    skills: [...counts].map(([id, count], index) => ({
      id,
      title: SKILL_TITLES[id] ?? id,
      version: '1.0.0',
      is_core: index < 2,
      target_questions: count,
    })),
    main_questions: limits.main,
    max_turns: limits.maxTurns,
    time_budget_minutes: limits.minutes,
    input_sources: sources,
    warnings: [],
  }
}

function threadOf(turn: TurnView): string {
  return turn.parent_question_id ?? turn.question_id
}

function mainQuestionId(index: number): string {
  return `q_${String(index + 1).padStart(3, '0')}`
}

function evidenceFrom(text: string, turnNo: number) {
  const quote = text.trim().slice(0, 120).trim()
  return quote ? [{ turn_no: turnNo, quote }] : []
}

function buildReport(session: SessionView): InterviewReport {
  const answered = session.turns.filter((t) => t.answer_text?.trim())
  const threads = new Map<string, TurnView[]>()
  for (const turn of answered) {
    threads.set(threadOf(turn), [...(threads.get(threadOf(turn)) ?? []), turn])
  }

  const questions: EvaluationResult[] = [...threads].map(([questionId, turns]) => {
    const first = turns[0] as TurnView
    const length = turns.reduce((sum, t) => sum + (t.answer_text?.length ?? 0), 0)
    const evidence = evidenceFrom(first.answer_text ?? '', first.turn_no)
    const base = {
      question_id: questionId,
      skill_id: first.skill_id,
      skill_version: '1.0.0',
      turn_nos: turns.map((t) => t.turn_no),
      covered_points: [],
      missed_points: [],
      strengths: [],
      gaps: [],
    }
    if (length < 25 || evidence.length === 0) {
      return {
        ...base,
        status: 'insufficient_evidence',
        weighted_score: null,
        criteria: Object.keys(STANDARD_WEIGHTS).map((id) => ({
          criterion_id: id,
          score: null,
          rationale: 'Câu trả lời quá ngắn để đánh giá.',
          evidence: [],
        })),
        improvement_suggestion: 'Hãy trả lời đầy đủ hơn: nêu ý chính, giải thích lý do và cho ví dụ.',
      }
    }
    const level = 2 + Math.min(2, Math.floor(length / 250))
    const scores: Record<string, number> = {
      technical_accuracy: clampScore(level + 0.5),
      completeness: clampScore(level),
      reasoning: clampScore(level),
      practical_examples: clampScore(level - 1 + (/\d/.test(first.answer_text ?? '') ? 1 : 0)),
    }
    const criteria: CriterionScore[] = Object.entries(scores).map(([id, score]) => ({
      criterion_id: id,
      score,
      rationale: 'Điểm mô phỏng dựa trên độ dài câu trả lời.',
      evidence,
    }))
    return {
      ...base,
      status: 'scored',
      criteria,
      weighted_score: round2(
        Object.entries(scores).reduce((sum, [id, s]) => sum + (STANDARD_WEIGHTS[id] ?? 0) * s, 0),
      ),
      improvement_suggestion: 'Báo cáo mô phỏng — nhận xét chi tiết sẽ có khi kết nối AI chấm điểm.',
    }
  })

  const bySkill = new Map<string, EvaluationResult[]>()
  for (const q of questions) bySkill.set(q.skill_id, [...(bySkill.get(q.skill_id) ?? []), q])
  const skillScores = [...bySkill].map(([skillId, results]) => {
    const scored = results.map((r) => r.weighted_score).filter((s): s is number => s !== null)
    return {
      skill_id: skillId,
      skill_version: '1.0.0',
      score: scored.length ? round2(scored.reduce((a, b) => a + b, 0) / scored.length) : null,
      question_ids: results.map((r) => r.question_id),
      summary: '',
    }
  })
  const assessed = skillScores.filter((s) => s.score !== null)
  const firstAnswer = answered[0]
  const crossEvidence = firstAnswer ? evidenceFrom(firstAnswer.answer_text ?? '', firstAnswer.turn_no) : []
  const cross = (id: string, score: number | null) => ({
    criterion_id: id,
    score: crossEvidence.length ? score : null,
    rationale: 'Điểm mô phỏng.',
    evidence: crossEvidence.length && score !== null ? crossEvidence : [],
  })

  return {
    session_id: session.id,
    role: session.role,
    level: session.level,
    mode: session.mode,
    overall_score: assessed.length
      ? round2(assessed.reduce((sum, s) => sum + (s.score ?? 0), 0) / assessed.length)
      : null,
    skill_scores: skillScores,
    cross_cutting: [
      {
        skill_id: 'communication',
        skill_version: '1.0.0',
        criteria: [cross('clarity', 3), cross('structure', 3)],
        summary: '',
      },
      {
        skill_id: 'problem_solving',
        skill_version: '1.0.0',
        criteria: [cross('decomposition', 3), cross('handling_uncertainty', null)],
        summary: '',
      },
    ],
    questions,
    top_strengths: [],
    priority_improvements: [],
    study_topics: [],
    versions: { rubric: '1.0.0', evaluator_prompt: 'mock' },
    disclaimer:
      'Đây là báo cáo mô phỏng để thử giao diện; điểm số chưa được chấm bằng AI và không phản ánh năng lực thật.',
    generated_at: now(),
  }
}

export function createMockApi({ latency = true }: { latency?: boolean } = {}): ApiClient {
  const records = loadRecords()
  const pause = (ms = LATENCY_MS) => (latency ? delay(ms) : Promise.resolve())

  const persist = () => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify([...records]))
    } catch {
      // Best effort only; the mock keeps working in memory.
    }
  }

  const get = (id: string): MockRecord => {
    const record = records.get(id)
    if (!record) throw new ApiError(404, 'Không tìm thấy phiên phỏng vấn.')
    return record
  }

  const view = (record: MockRecord): SessionView => structuredClone(record.session)

  const addMainTurn = (record: MockRecord, index: number) => {
    const question = record.script[index]
    if (!question) return
    record.session.turns.push({
      turn_no: record.session.turns.length + 1,
      question_id: mainQuestionId(index),
      parent_question_id: null,
      kind: 'main',
      skill_id: question.skillId,
      question_text: question.text,
      answer_text: null,
      asked_at: now(),
      answered_at: null,
    })
  }

  const finish = (record: MockRecord, reason: EndReason) => {
    const { session } = record
    session.status = 'completed'
    session.ended_at = now()
    session.end_reason = reason
    session.report_status = 'completed'
    record.report = buildReport(session)
  }

  return {
    supportsLiveInterview: true,
    supportsReport: true,

    async createInterview(setup, files) {
      await pause(600)
      const id = crypto.randomUUID()
      const docs = { cv: Boolean(setup.cv_text || files?.cv), jd: Boolean(setup.jd_text || files?.jd) }
      const session: SessionView = {
        id,
        role: setup.role,
        level: setup.level,
        mode: setup.mode,
        status: 'ready',
        has_cv: docs.cv,
        has_jd: docs.jd,
        created_at: now(),
        started_at: null,
        ended_at: null,
        end_reason: null,
        plan_preview: null,
        turns: [],
        report_status: null,
      }
      const script = scriptFor(session, docs.cv)
      session.plan_preview = previewFor(setup, script, docs)
      records.set(id, { session, report: null, script, processedRequests: [] })
      persist()
      return structuredClone(session)
    },

    async prepareInterview(id) {
      await pause()
      return view(get(id))
    },

    async getInterview(id) {
      await pause()
      return view(get(id))
    },

    async listInterviews() {
      await pause()
      return [...records.values()]
        .map(({ session, report }): SessionSummary => ({
          id: session.id,
          role: session.role,
          level: session.level,
          mode: session.mode,
          status: session.status,
          has_cv: session.has_cv,
          has_jd: session.has_jd,
          created_at: session.created_at,
          ended_at: session.ended_at,
          report_status: session.report_status,
          overall_score: report?.overall_score ?? null,
        }))
        .sort((a, b) => b.created_at.localeCompare(a.created_at))
    },

    async startInterview(id) {
      await pause()
      const record = get(id)
      if (record.session.status !== 'ready') throw new ApiError(409, 'Phiên không ở trạng thái sẵn sàng.')
      record.session.status = 'in_progress'
      record.session.started_at = now()
      addMainTurn(record, 0)
      persist()
      return view(record)
    },

    async submitAnswer(id, submission: AnswerSubmission) {
      await pause(500)
      const record = get(id)
      const { session } = record
      if (record.processedRequests.includes(submission.request_id)) return view(record)
      if (session.status !== 'in_progress') throw new ApiError(409, 'Phiên phỏng vấn đã kết thúc.')
      const pending = session.turns.at(-1)
      if (!pending || pending.answer_text !== null) throw new ApiError(409, 'Không có câu hỏi đang chờ.')
      if (pending.turn_no !== submission.turn_no) {
        throw new ApiError(409, 'Câu hỏi đã thay đổi. Hãy tải lại trang.')
      }
      const answer = submission.answer_text.trim()
      if (!answer) throw new ApiError(422, 'Câu trả lời không được để trống.')

      pending.answer_text = answer
      pending.answered_at = now()
      record.processedRequests.push(submission.request_id)

      const limits = LIMITS[session.mode]
      const root = threadOf(pending)
      const mainAsked = session.turns.filter((t) => t.kind === 'main').length
      const followUps = session.turns.filter((t) => t.parent_question_id === root).length
      const current = record.script[mainAsked - 1]

      if (session.turns.length >= limits.maxTurns) {
        finish(record, 'max_turns')
      } else if (followUps < limits.followUps && answer.length < SHORT_ANSWER_CHARS && current) {
        session.turns.push({
          turn_no: session.turns.length + 1,
          question_id: `${root}.f${followUps + 1}`,
          parent_question_id: root,
          kind: 'follow_up',
          skill_id: pending.skill_id,
          question_text: current.followUp,
          answer_text: null,
          asked_at: now(),
          answered_at: null,
        })
      } else if (mainAsked < limits.main) {
        addMainTurn(record, mainAsked)
      } else {
        finish(record, 'plan_completed')
      }
      persist()
      return view(record)
    },

    async finishInterview(id) {
      await pause()
      const record = get(id)
      if (record.session.status === 'in_progress') finish(record, 'user_ended')
      persist()
      return view(record)
    },

    async getReport(id): Promise<ReportResponse> {
      await pause()
      const record = get(id)
      if (!record.session.report_status) throw new ApiError(404, 'Phiên chưa kết thúc nên chưa có báo cáo.')
      return { status: record.session.report_status, report: structuredClone(record.report) }
    },

    async retryReport(id) {
      return this.getReport(id)
    },

    async deleteInterview(id) {
      await pause()
      get(id)
      records.delete(id)
      persist()
    },

    // Mock mode has no server speech: questions use the browser voice; recording is disabled.
    async speechCapabilities() {
      return { stt: false, tts: false, tts_provider: null }
    },

    async transcribe() {
      throw new ApiError(501, 'Chế độ mô phỏng không hỗ trợ ghi âm.')
    },

    async questionAudio() {
      throw new ApiError(501, 'Chế độ mô phỏng không có giọng đọc máy chủ.')
    },
  }
}
