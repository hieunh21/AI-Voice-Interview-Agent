import { afterEach, describe, expect, it, vi } from 'vitest'
import { createHttpApi, type TokenStore } from './http'
import { ApiError } from './types'

function memoryStore(initial: string | null = null): TokenStore {
  let token = initial
  return {
    get: () => token,
    set: (value) => {
      token = value
    },
    clear: () => {
      token = null
    },
  }
}

const json = (status: number, body: unknown) =>
  new Response(status === 204 ? null : JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

type Call = { url: string; init: RequestInit }

function stubFetch(responses: Response[]): Call[] {
  const calls: Call[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init: RequestInit) => {
      calls.push({ url, init })
      const next = responses.shift()
      if (!next) throw new Error('unexpected request')
      return next
    }),
  )
  return calls
}

afterEach(() => vi.unstubAllGlobals())

describe('http api client', () => {
  it('creates a guest token once and sends it as a bearer token', async () => {
    const store = memoryStore()
    const calls = stubFetch([json(201, { token: 'tok-1' }), json(200, []), json(200, [])])
    const api = createHttpApi('http://api.test/', store)
    await api.listInterviews()
    await api.listInterviews()
    expect(calls.map((c) => c.url)).toEqual([
      'http://api.test/api/auth/guest',
      'http://api.test/api/interviews',
      'http://api.test/api/interviews',
    ])
    expect((calls[1]?.init.headers as Record<string, string>).Authorization).toBe('Bearer tok-1')
    expect(store.get()).toBe('tok-1')
  })

  it('creates, uploads files and prepares in order', async () => {
    const calls = stubFetch([
      json(201, { id: 's1' }),
      json(200, { id: 's1' }),
      json(200, { id: 's1', status: 'ready' }),
    ])
    const api = createHttpApi('http://api.test', memoryStore('tok'))
    const cv = new File(['%PDF-1.4'], 'cv.pdf', { type: 'application/pdf' })
    const session = await api.createInterview({ role: 'ai_engineer', level: 'fresher', mode: 'demo' }, { cv })
    expect(session.status).toBe('ready')
    expect(calls.map((c) => `${c.init.method} ${c.url}`)).toEqual([
      'POST http://api.test/api/interviews',
      'POST http://api.test/api/interviews/s1/cv',
      'POST http://api.test/api/interviews/s1/prepare',
    ])
    expect(calls[1]?.init.body).toBeInstanceOf(FormData)
  })

  it('maps backend errors to ApiError with the server message', async () => {
    stubFetch([json(422, { detail: 'PDF không có lớp text.' })])
    const api = createHttpApi('http://api.test', memoryStore('tok'))
    await expect(api.getInterview('x')).rejects.toEqual(new ApiError(422, 'PDF không có lớp text.'))
  })

  it('replaces an invalid token once on 401', async () => {
    const store = memoryStore('stale')
    stubFetch([json(401, { detail: 'invalid' }), json(201, { token: 'fresh' }), json(200, [])])
    const api = createHttpApi('http://api.test', store)
    await expect(api.listInterviews()).resolves.toEqual([])
    expect(store.get()).toBe('fresh')
  })

  it('reports an unreachable backend clearly', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    const api = createHttpApi('http://api.test', memoryStore('tok'))
    await expect(api.listInterviews()).rejects.toMatchObject({ status: 0 })
  })

  it('drives the live interview through start, answer and finish', async () => {
    const calls = stubFetch([
      json(200, { id: 's1', status: 'in_progress' }),
      json(200, { id: 's1', status: 'in_progress' }),
      json(200, { id: 's1', status: 'completed' }),
    ])
    const api = createHttpApi('http://api.test', memoryStore('tok'))
    expect(api.supportsLiveInterview).toBe(true)
    await api.startInterview('s1')
    await api.submitAnswer('s1', { request_id: 'req-12345', turn_no: 1, answer_text: 'Trả lời' })
    await api.finishInterview('s1')
    expect(calls.map((c) => `${c.init.method} ${c.url}`)).toEqual([
      'POST http://api.test/api/interviews/s1/start',
      'POST http://api.test/api/interviews/s1/answer',
      'POST http://api.test/api/interviews/s1/finish',
    ])
    expect(JSON.parse(calls[1]?.init.body as string)).toEqual({
      request_id: 'req-12345',
      turn_no: 1,
      answer_text: 'Trả lời',
    })
  })

  it('uploads recordings and fetches question audio with the guest token', async () => {
    const calls = stubFetch([
      json(200, { text: 'Em dùng RAG', latency_ms: 900 }),
      new Response(new Blob(['mp3']), { status: 200, headers: { 'Content-Type': 'audio/mpeg' } }),
      json(200, { stt: true, tts: true, tts_provider: 'elevenlabs' }),
    ])
    const api = createHttpApi('http://api.test', memoryStore('tok'))
    const transcript = await api.transcribe('s1', new Blob(['RIFF'], { type: 'audio/wav' }))
    const audio = await api.questionAudio('s1', 3)
    const caps = await api.speechCapabilities()

    expect(transcript.text).toBe('Em dùng RAG')
    expect(await audio.text()).toBe('mp3')
    expect(caps).toEqual({ stt: true, tts: true, tts_provider: 'elevenlabs' })
    expect(calls.map((c) => `${c.init.method} ${c.url}`)).toEqual([
      'POST http://api.test/api/interviews/s1/transcribe',
      'GET http://api.test/api/interviews/s1/turns/3/audio',
      'GET http://api.test/api/speech/capabilities',
    ])
    const form = calls[0]?.init.body as FormData
    expect((form.get('file') as File).name).toBe('answer.wav')
    expect((calls[1]?.init.headers as Record<string, string>).Authorization).toBe('Bearer tok')
  })

  it('reads and retries reports', async () => {
    const calls = stubFetch([
      json(200, { status: 'processing', report: null }),
      json(200, { status: 'pending', report: null }),
    ])
    const api = createHttpApi('http://api.test', memoryStore('tok'))
    expect(api.supportsReport).toBe(true)
    expect((await api.getReport('s1')).status).toBe('processing')
    expect((await api.retryReport('s1')).status).toBe('pending')
    expect(calls.map((c) => `${c.init.method} ${c.url}`)).toEqual([
      'GET http://api.test/api/interviews/s1/report',
      'POST http://api.test/api/interviews/s1/report/retry',
    ])
  })
})
