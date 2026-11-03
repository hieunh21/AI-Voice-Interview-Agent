import { createMockApi } from './mock'
import type { ApiClient } from './types'

export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

/** Phase 0 serves interview data from in-browser mocks; the HTTP client replaces it in Phase 1–2. */
export const USING_MOCKS = true

export const api: ApiClient = createMockApi()
