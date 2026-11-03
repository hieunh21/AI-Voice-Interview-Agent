// Audio helpers for turn-based voice. Recordings are converted to 16 kHz mono WAV in the browser:
// every STT provider accepts it, and the backend can check the duration from the header.

export const TARGET_SAMPLE_RATE = 16_000
export const MAX_RECORDING_SECONDS = 180

const RECORDER_TYPES = ['audio/webm;codecs=opus', 'audio/ogg;codecs=opus', 'audio/webm', 'audio/mp4']

export function pickRecorderMimeType(isSupported: (type: string) => boolean): string | undefined {
  return RECORDER_TYPES.find((type) => isSupported(type))
}

/** 16-bit PCM mono WAV from samples in [-1, 1] (values outside are clipped). */
export function encodeWav(samples: Float32Array, sampleRate: number): ArrayBuffer {
  const buffer = new ArrayBuffer(44 + samples.length * 2)
  const view = new DataView(buffer)
  const ascii = (offset: number, text: string) => {
    for (let i = 0; i < text.length; i++) view.setUint8(offset + i, text.charCodeAt(i))
  }
  ascii(0, 'RIFF')
  view.setUint32(4, 36 + samples.length * 2, true)
  ascii(8, 'WAVE')
  ascii(12, 'fmt ')
  view.setUint32(16, 16, true) // fmt chunk size
  view.setUint16(20, 1, true) // PCM
  view.setUint16(22, 1, true) // mono
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true) // byte rate
  view.setUint16(32, 2, true) // block align
  view.setUint16(34, 16, true) // bits per sample
  ascii(36, 'data')
  view.setUint32(40, samples.length * 2, true)
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i] ?? 0))
    view.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true)
  }
  return buffer
}

/** Decode any recorder output and resample it to 16 kHz mono WAV (browser only). */
export async function toWav16kMono(recording: Blob): Promise<Blob> {
  const context = new AudioContext()
  try {
    const decoded = await context.decodeAudioData(await recording.arrayBuffer())
    const frames = Math.max(1, Math.ceil(decoded.duration * TARGET_SAMPLE_RATE))
    const offline = new OfflineAudioContext(1, frames, TARGET_SAMPLE_RATE)
    const source = offline.createBufferSource()
    source.buffer = decoded
    source.connect(offline.destination)
    source.start()
    const rendered = await offline.startRendering()
    return new Blob([encodeWav(rendered.getChannelData(0), TARGET_SAMPLE_RATE)], { type: 'audio/wav' })
  } finally {
    void context.close()
  }
}

export function formatSeconds(total: number): string {
  const minutes = Math.floor(total / 60)
  const seconds = Math.floor(total % 60)
  return `${minutes}:${String(seconds).padStart(2, '0')}`
}

/** Speak with the browser's built-in voice (fallback when server TTS is unavailable). */
export function speakWithBrowser(
  text: string,
  handlers: { onStart?: () => void; onEnd?: () => void } = {},
): boolean {
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) return false
  const utterance = new SpeechSynthesisUtterance(text)
  utterance.lang = 'vi-VN'
  const voice = window.speechSynthesis.getVoices().find((v) => v.lang.toLowerCase().startsWith('vi'))
  if (voice) utterance.voice = voice
  utterance.rate = 1
  utterance.onstart = () => handlers.onStart?.()
  utterance.onend = () => handlers.onEnd?.()
  utterance.onerror = () => handlers.onEnd?.()
  window.speechSynthesis.cancel()
  window.speechSynthesis.speak(utterance)
  return true
}
