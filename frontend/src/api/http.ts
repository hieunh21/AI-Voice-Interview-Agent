import {
  ApiError,
  type ApiClient,
  type InterviewSetup,
  type ReportResponse,
  type SessionSummary,
  type SessionView,
  type SetupFiles,
  type SpeechCapabilities,
  type Transcript,
} from './types'

const TOKEN_KEY = 'intervai.guestToken'
const OFFLINE = 'Không kết nối được máy chủ. Hãy kiểm tra backend đang chạy.'

export interface TokenStore {
  get(): string | null
  set(token: string): void
  clear(): void
}

/** localStorage when available; in-memory otherwise (private mode, blocked storage). */
export function browserTokenStore(): TokenStore {
  let memory: string | null = null
  return {
    get() {
      try {
        return localStorage.getItem(TOKEN_KEY) ?? memory
      } catch {
        return memory
      }
    },
    set(token) {
      memory = token
      try {
        localStorage.setItem(TOKEN_KEY, token)
      } catch {
        // keep the in-memory copy
      }
    },
    clear() {
      memory = null
      try {
        localStorage.removeItem(TOKEN_KEY)
      } catch {
        // nothing to clear
      }
    },
  }
}

async function toApiError(response: Response): Promise<ApiError> {
  let message = `Lỗi máy chủ (${response.status}).`
  try {
    const body = (await response.json()) as { detail?: unknown }
    if (typeof body.detail === 'string') message = body.detail
    else if (Array.isArray(body.detail)) message = 'Dữ liệu gửi lên không hợp lệ.'
  } catch {
    // non-JSON error body
  }
  return new ApiError(response.status, message)
}

export function createHttpApi(baseUrl: string, tokens: TokenStore = browserTokenStore()): ApiClient {
  const base = baseUrl.replace(/\/$/, '')

  async function send(path: string, init: RequestInit): Promise<Response> {
    try {
      return await fetch(`${base}${path}`, init)
    } catch {
      throw new ApiError(0, OFFLINE)
    }
  }

  async function token(): Promise<string> {
    const existing = tokens.get()
    if (existing) return existing
    const response = await send('/api/auth/guest', { method: 'POST' })
    if (!response.ok) throw await toApiError(response)
    const { token: created } = (await response.json()) as { token: string }
    tokens.set(created)
    return created
  }

  async function authed(method: string, path: string, body?: unknown, retried = false): Promise<Response> {
    const headers: Record<string, string> = { Authorization: `Bearer ${await token()}` }
    let payload: BodyInit | undefined
    if (body instanceof FormData) {
      payload = body
    } else if (body !== undefined) {
      headers['Content-Type'] = 'application/json'
      payload = JSON.stringify(body)
    }
    const response = await send(path, { method, headers, body: payload })
    if (response.status === 401 && !retried) {
      // Token lost or revoked: start a fresh guest identity once.
      tokens.clear()
      return authed(method, path, body, true)
    }
    if (!response.ok) throw await toApiError(response)
    return response
  }

  async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const response = await authed(method, path, body)
    if (response.status === 204) return undefined as T
    return (await response.json()) as T
  }

  return {
    supportsLiveInterview: true,
    supportsReport: true,

    async createInterview(setup: InterviewSetup, files?: SetupFiles) {
      const created = await request<SessionView>('POST', '/api/interviews', setup)
      for (const kind of ['cv', 'jd'] as const) {
        const file = files?.[kind]
        if (!file) continue
        const form = new FormData()
        form.append('file', file)
        await request<SessionView>('POST', `/api/interviews/${created.id}/${kind}`, form)
      }
      return request<SessionView>('POST', `/api/interviews/${created.id}/prepare`)
    },

    prepareInterview: (id) => request<SessionView>('POST', `/api/interviews/${id}/prepare`),
    getInterview: (id) => request<SessionView>('GET', `/api/interviews/${id}`),
    listInterviews: () => request<SessionSummary[]>('GET', '/api/interviews'),
    deleteInterview: (id) => request<void>('DELETE', `/api/interviews/${id}`),

    startInterview: (id) => request<SessionView>('POST', `/api/interviews/${id}/start`),
    submitAnswer: (id, submission) =>
      request<SessionView>('POST', `/api/interviews/${id}/answer`, submission),
    finishInterview: (id) => request<SessionView>('POST', `/api/interviews/${id}/finish`),
    getReport: (id) => request<ReportResponse>('GET', `/api/interviews/${id}/report`),
    retryReport: (id) => request<ReportResponse>('POST', `/api/interviews/${id}/report/retry`),

    async speechCapabilities() {
      const response = await send('/api/speech/capabilities', { method: 'GET' })
      if (!response.ok) throw await toApiError(response)
      return (await response.json()) as SpeechCapabilities
    },

    transcribe(id, audio) {
      const form = new FormData()
      form.append('file', audio, 'answer.wav')
      return request<Transcript>('POST', `/api/interviews/${id}/transcribe`, form)
    },

    async questionAudio(id, turnNo) {
      const response = await authed('GET', `/api/interviews/${id}/turns/${turnNo}/audio`)
      return response.blob()
    },
  }
}
