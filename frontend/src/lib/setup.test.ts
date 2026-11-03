import { describe, expect, it } from 'vitest'
import { EMPTY_SETUP, MAX_CV_CHARS, toSetupPayload, validateSetup } from './setup'

describe('validateSetup', () => {
  it('requires role and level', () => {
    expect(validateSetup(EMPTY_SETUP)).toEqual({
      role: 'Chọn vị trí ứng tuyển.',
      level: 'Chọn cấp độ.',
    })
  })

  it('accepts role + level without any document', () => {
    expect(validateSetup({ ...EMPTY_SETUP, role: 'ai_engineer', level: 'fresher' })).toEqual({})
  })

  it('limits CV length', () => {
    const errors = validateSetup({
      ...EMPTY_SETUP,
      role: 'ai_engineer',
      level: 'fresher',
      cvText: 'x'.repeat(MAX_CV_CHARS + 1),
    })
    expect(errors.cvText).toBeDefined()
  })
})

describe('toSetupPayload', () => {
  it('omits blank documents', () => {
    expect(
      toSetupPayload({ ...EMPTY_SETUP, role: 'data_engineer', level: 'junior', cvText: '   ' }),
    ).toEqual({ role: 'data_engineer', level: 'junior', mode: 'demo' })
  })

  it('trims provided documents', () => {
    const payload = toSetupPayload({
      ...EMPTY_SETUP,
      role: 'backend_developer',
      level: 'intern',
      mode: 'standard',
      jdText: '  Yêu cầu Python, Docker  ',
    })
    expect(payload).toEqual({
      role: 'backend_developer',
      level: 'intern',
      mode: 'standard',
      jd_text: 'Yêu cầu Python, Docker',
    })
  })

  it('throws without role or level', () => {
    expect(() => toSetupPayload(EMPTY_SETUP)).toThrow()
  })
})
