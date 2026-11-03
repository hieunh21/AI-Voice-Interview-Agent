import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { speakWithBrowser } from './audio'

interface Options {
  sessionId: string
  turnNo: number | undefined
  text: string | undefined
  /** Read new questions aloud automatically. */
  autoplay: boolean
  /** The server offers TTS (ElevenLabs); otherwise the browser voice is used. */
  serverTts: boolean
}

/** Reads the pending question aloud: server TTS first, browser voice as fallback. */
export function useQuestionVoice({ sessionId, turnNo, text, autoplay, serverTts }: Options) {
  const [speaking, setSpeaking] = useState(false)
  const audio = useRef<HTMLAudioElement | null>(null)
  const objectUrl = useRef<string | null>(null)

  const stop = useCallback(() => {
    audio.current?.pause()
    audio.current = null
    if (objectUrl.current) URL.revokeObjectURL(objectUrl.current)
    objectUrl.current = null
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) window.speechSynthesis.cancel()
  }, [])

  const speak = useCallback(async () => {
    stop()
    if (!text || turnNo === undefined) return
    const handlers = { onStart: () => setSpeaking(true), onEnd: () => setSpeaking(false) }
    if (serverTts) {
      try {
        const blob = await api.questionAudio(sessionId, turnNo)
        const url = URL.createObjectURL(blob)
        const player = new Audio(url)
        objectUrl.current = url
        audio.current = player
        player.onplay = handlers.onStart
        player.onended = handlers.onEnd
        player.onpause = handlers.onEnd
        await player.play()
        return
      } catch {
        // Server TTS unavailable or autoplay blocked: fall back to the browser voice.
      }
    }
    speakWithBrowser(text, handlers)
  }, [serverTts, sessionId, stop, text, turnNo])

  useEffect(() => {
    if (autoplay && turnNo !== undefined) void speak()
    return stop
  }, [autoplay, speak, stop, turnNo])

  return { speaking, speak, stop }
}
