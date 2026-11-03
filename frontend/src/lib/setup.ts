import type { InterviewMode, InterviewSetup, Level, Role } from '../api/types'

// Same limits as ai/schemas/interview.py (MAX_CV_CHARS / MAX_JD_CHARS).
export const MAX_CV_CHARS = 20_000
export const MAX_JD_CHARS = 15_000

export interface SetupForm {
  role: Role | null
  level: Level | null
  mode: InterviewMode
  cvText: string
  jdText: string
}

export type SetupErrors = Partial<Record<'role' | 'level' | 'cvText' | 'jdText', string>>

export const EMPTY_SETUP: SetupForm = {
  role: null,
  level: null,
  mode: 'demo',
  cvText: '',
  jdText: '',
}

/** Role and level are the only required inputs; CV/JD are optional and only length-limited. */
export function validateSetup(form: SetupForm): SetupErrors {
  const errors: SetupErrors = {}
  if (!form.role) errors.role = 'Chọn vị trí ứng tuyển.'
  if (!form.level) errors.level = 'Chọn cấp độ.'
  if (form.cvText.trim().length > MAX_CV_CHARS) {
    errors.cvText = `CV tối đa ${MAX_CV_CHARS.toLocaleString('vi-VN')} ký tự.`
  }
  if (form.jdText.trim().length > MAX_JD_CHARS) {
    errors.jdText = `JD tối đa ${MAX_JD_CHARS.toLocaleString('vi-VN')} ký tự.`
  }
  return errors
}

/** Build the API payload; blank documents are omitted rather than sent as empty strings. */
export function toSetupPayload(form: SetupForm): InterviewSetup {
  if (!form.role || !form.level) throw new Error('role and level are required')
  const payload: InterviewSetup = { role: form.role, level: form.level, mode: form.mode }
  const cv = form.cvText.trim()
  const jd = form.jdText.trim()
  if (cv) payload.cv_text = cv
  if (jd) payload.jd_text = jd
  return payload
}
