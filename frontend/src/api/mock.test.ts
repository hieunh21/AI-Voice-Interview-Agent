import { describe, expect, it } from 'vitest'
import { createMockApi } from './mock'
import { ApiError, type ApiClient, type SessionView } from './types'

const SHORT = 'Em nghĩ là dùng embedding.'
const LONG = 'Câu trả lời đầy đủ. '.repeat(15)

async function answerPending(api: ApiClient, session: SessionView, text: string) {
  return api.submitAnswer(session.id, { request_id: crypto.randomUUID(), answer_text: text })
}

describe('mock API', () => {
  it('creates a ready session from role + level only', async () => {
    const api = createMockApi({ latency: false })
    const session = await api.createInterview({ role: 'ai_engineer', level: 'fresher', mode: 'demo' })
    expect(session.status).toBe('ready')
    expect(session.has_cv).toBe(false)
    expect(session.plan_preview?.main_questions).toBe(3)
    expect(session.plan_preview?.input_sources).toEqual([
      'role_config',
      'role_playbook',
      'competency_skills',
    ])
  })

  it('runs a full demo interview with bounded follow-ups and a report', async () => {
    const api = createMockApi({ latency: false })
    let session = await api.createInterview({ role: 'data_engineer', level: 'intern', mode: 'demo' })
    await expect(api.getReport(session.id)).rejects.toBeInstanceOf(ApiError)

    session = await api.startInterview(session.id)
    expect(session.turns).toHaveLength(1)

    session = await answerPending(api, session, SHORT) // short answer → follow-up
    expect(session.turns.at(-1)?.kind).toBe('follow_up')
    expect(session.turns.at(-1)?.question_id).toBe('q_001.f1')

    session = await answerPending(api, session, SHORT) // demo allows 1 follow-up → next main
    expect(session.turns.at(-1)?.question_id).toBe('q_002')

    while (session.status === 'in_progress') session = await answerPending(api, session, LONG)

    expect(session.status).toBe('completed')
    expect(session.end_reason).toBe('plan_completed')
    expect(session.turns.length).toBeLessThanOrEqual(session.plan_preview?.max_turns ?? 0)
    expect(session.turns.filter((t) => t.kind === 'main')).toHaveLength(3)

    const { status, report } = await api.getReport(session.id)
    expect(status).toBe('completed')
    expect(report?.questions.map((q) => q.question_id)).toEqual(['q_001', 'q_002', 'q_003'])
    const answers = new Map(session.turns.map((t) => [t.turn_no, t.answer_text ?? '']))
    for (const criterion of report?.questions.flatMap((q) => q.criteria) ?? []) {
      for (const evidence of criterion.evidence) {
        expect(answers.get(evidence.turn_no)).toContain(evidence.quote)
      }
    }
  })

  it('treats a retried answer with the same request id as a no-op', async () => {
    const api = createMockApi({ latency: false })
    const created = await api.createInterview({ role: 'backend_developer', level: 'junior', mode: 'demo' })
    const started = await api.startInterview(created.id)
    const submission = { request_id: crypto.randomUUID(), answer_text: LONG }
    const first = await api.submitAnswer(started.id, submission)
    const retry = await api.submitAnswer(started.id, submission)
    expect(retry.turns).toEqual(first.turns)
  })

  it('personalises the opening question when a CV is provided', async () => {
    const api = createMockApi({ latency: false })
    const created = await api.createInterview({
      role: 'ai_engineer',
      level: 'junior',
      mode: 'standard',
      cv_text: 'Dự án chatbot RAG dùng LangGraph',
    })
    expect(created.plan_preview?.input_sources).toContain('cv')
    const started = await api.startInterview(created.id)
    expect(started.turns[0]?.question_text).toContain('CV')
  })

  it('ends early on request and still produces a report', async () => {
    const api = createMockApi({ latency: false })
    const created = await api.createInterview({ role: 'ai_engineer', level: 'intern', mode: 'standard' })
    let session = await api.startInterview(created.id)
    session = await answerPending(api, session, LONG)
    session = await api.finishInterview(session.id)
    expect(session.end_reason).toBe('user_ended')
    expect((await api.getReport(session.id)).report?.questions).toHaveLength(1)
  })

  it('serves the four fixtures, newest first', async () => {
    const api = createMockApi({ latency: false })
    const sessions = await api.listInterviews()
    expect(sessions.map((s) => [s.has_cv, s.has_jd])).toEqual(
      expect.arrayContaining([
        [false, false],
        [true, false],
        [false, true],
        [true, true],
      ]),
    )
    const dates = sessions.map((s) => s.created_at)
    expect(dates).toEqual([...dates].sort().reverse())
  })
})
