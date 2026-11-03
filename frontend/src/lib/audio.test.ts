import { describe, expect, it } from 'vitest'
import { encodeWav, formatSeconds, pickRecorderMimeType } from './audio'

const ascii = (view: DataView, offset: number, length: number) =>
  String.fromCharCode(...Array.from({ length }, (_, i) => view.getUint8(offset + i)))

describe('encodeWav', () => {
  it('writes a 16-bit mono PCM header the backend can read', () => {
    const view = new DataView(encodeWav(new Float32Array(16_000), 16_000))
    expect(ascii(view, 0, 4)).toBe('RIFF')
    expect(ascii(view, 8, 4)).toBe('WAVE')
    expect(view.getUint16(22, true)).toBe(1) // mono
    expect(view.getUint32(24, true)).toBe(16_000)
    expect(view.getUint32(28, true)).toBe(32_000) // byte rate → 1 s of audio
    expect(view.getUint32(40, true)).toBe(32_000)
    expect(view.byteLength).toBe(44 + 32_000)
  })

  it('clips samples outside [-1, 1]', () => {
    const view = new DataView(encodeWav(new Float32Array([2, -2, 0.5]), 16_000))
    expect(view.getInt16(44, true)).toBe(0x7fff)
    expect(view.getInt16(46, true)).toBe(-0x8000)
    expect(view.getInt16(48, true)).toBe(Math.trunc(0.5 * 0x7fff))
  })
})

describe('recorder helpers', () => {
  it('prefers opus and falls back to what the browser supports', () => {
    expect(pickRecorderMimeType(() => true)).toBe('audio/webm;codecs=opus')
    expect(pickRecorderMimeType((t) => t === 'audio/mp4')).toBe('audio/mp4')
    expect(pickRecorderMimeType(() => false)).toBeUndefined()
  })

  it('formats the recording timer', () => {
    expect(formatSeconds(0)).toBe('0:00')
    expect(formatSeconds(75)).toBe('1:15')
    expect(formatSeconds(180)).toBe('3:00')
  })
})
