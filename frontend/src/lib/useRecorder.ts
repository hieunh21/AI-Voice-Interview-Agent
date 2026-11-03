import { useCallback, useEffect, useRef, useState } from 'react'
import { MAX_RECORDING_SECONDS, pickRecorderMimeType, toWav16kMono } from './audio'
import { errorMessage } from './errors'

export type RecorderStatus = 'idle' | 'recording' | 'processing'

function micErrorMessage(error: unknown): string {
  const name = error instanceof DOMException ? error.name : ''
  if (name === 'NotAllowedError' || name === 'SecurityError') {
    return 'Trình duyệt chưa được cho phép dùng micro. Hãy cấp quyền micro hoặc gõ câu trả lời.'
  }
  if (name === 'NotFoundError') return 'Không tìm thấy micro. Bạn có thể gõ câu trả lời.'
  return 'Không mở được micro. Bạn có thể gõ câu trả lời.'
}

/**
 * Record one answer with MediaRecorder, convert it to 16 kHz WAV and hand it to `onAudio`.
 * Stops automatically after MAX_RECORDING_SECONDS. Errors never block the text fallback.
 */
export function useRecorder(onAudio: (wav: Blob) => Promise<void>) {
  const [status, setStatus] = useState<RecorderStatus>('idle')
  const [seconds, setSeconds] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const recorder = useRef<MediaRecorder | null>(null)
  const stream = useRef<MediaStream | null>(null)
  const timer = useRef<number | null>(null)
  const discard = useRef(false)
  const onAudioRef = useRef(onAudio)

  useEffect(() => {
    onAudioRef.current = onAudio
  }, [onAudio])

  const supported =
    typeof window !== 'undefined' &&
    typeof MediaRecorder !== 'undefined' &&
    Boolean(navigator.mediaDevices?.getUserMedia)

  const release = useCallback(() => {
    if (timer.current !== null) window.clearInterval(timer.current)
    timer.current = null
    stream.current?.getTracks().forEach((track) => track.stop())
    stream.current = null
  }, [])

  const stop = useCallback(() => {
    if (recorder.current?.state === 'recording') recorder.current.stop()
  }, [])

  const start = useCallback(async () => {
    if (!supported || recorder.current?.state === 'recording') return
    setError(null)
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true },
      })
    } catch (err) {
      setError(micErrorMessage(err))
      return
    }
    const mimeType = pickRecorderMimeType((type) => MediaRecorder.isTypeSupported(type))
    const media = new MediaRecorder(stream.current, mimeType ? { mimeType } : undefined)
    const chunks: Blob[] = []
    discard.current = false
    media.ondataavailable = (event) => {
      if (event.data.size > 0) chunks.push(event.data)
    }
    media.onstop = async () => {
      release()
      if (discard.current) return
      setStatus('processing')
      try {
        const wav = await toWav16kMono(new Blob(chunks, { type: media.mimeType }))
        await onAudioRef.current(wav)
      } catch (err) {
        setError(err instanceof DOMException ? 'Không đọc được bản ghi âm. Hãy thử lại.' : errorMessage(err))
      } finally {
        setStatus('idle')
      }
    }
    recorder.current = media
    media.start()
    setSeconds(0)
    setStatus('recording')
    timer.current = window.setInterval(() => setSeconds((value) => value + 1), 1000)
  }, [release, supported])

  useEffect(() => {
    if (status === 'recording' && seconds >= MAX_RECORDING_SECONDS) stop()
  }, [seconds, status, stop])

  useEffect(
    () => () => {
      discard.current = true
      if (recorder.current?.state === 'recording') recorder.current.stop()
      release()
    },
    [release],
  )

  return { supported, status, seconds, error, start, stop }
}
