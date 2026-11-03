import { createHttpApi } from './http'
import { createMockApi } from './mock'
import type { ApiClient } from './types'

export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

/** `http` (default) talks to the FastAPI backend; `mock` runs fully in the browser. */
export const USING_MOCKS = import.meta.env.VITE_API_MODE === 'mock'

export const api: ApiClient = USING_MOCKS ? createMockApi() : createHttpApi(API_BASE_URL)
