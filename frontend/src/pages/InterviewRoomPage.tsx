import { useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { api } from '../api'
import { ApiError, type SessionView, type SpeechCapabilities } from '../api/types'
import { PlanPreviewCard } from '../components/PlanPreviewCard'
import { Transcript } from '../components/Transcript'
import { Badge, Button, Card, Notice, Spinner } from '../components/ui'
import { errorMessage } from '../lib/errors'
import { SESSION_STATUS_LABELS, TURN_KIND_LABELS } from '../lib/labels'
import { formatSeconds, MAX_RECORDING_SECONDS } from '../lib/audio'
import { useLoader } from '../lib/useLoader'
import { useQuestionVoice } from '../lib/useQuestionVoice'
import { useRecorder } from '../lib/useRecorder'

const MAX_ANSWER_CHARS = 4000
const loadSession = (id: string) => api.getInterview(id)

export default function InterviewRoomPage() {
  const { id = '' } = useParams()
  const { data: session, error, loading, setData } = useLoader(id, loadSession)

  if (loading) return <Spinner />
  if (error || !session) return <Notice title="Không mở được phiên phỏng vấn">{error}</Notice>

  if (session.status === 'ready') return <ReadyView session={session} onChange={setData} />
  if (session.status === 'in_progress') return <LiveView session={session} onChange={setData} />
  if (session.status === 'completed') return <CompletedView session={session} />
  if (session.status === 'created' || session.status === 'failed') {
    return <PrepareView session={session} onChange={setData} />
  }
  return <Notice title={`Phiên đang ở trạng thái: ${SESSION_STATUS_LABELS[session.status]}`} tone="amber" />
}

function PrepareView({ session, onChange }: { session: SessionView; onChange: (s: SessionView) => void }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function prepare() {
    setBusy(true)
    setError(null)
    try {
      onChange(await api.prepareInterview(session.id))
    } catch (err) {
      setError(errorMessage(err))
      setBusy(false)
    }
  }

  return (
    <Card className="space-y-4">
      <h1 className="text-xl font-semibold">Kế hoạch phỏng vấn chưa được tạo</h1>
      <p className="text-sm text-slate-600">
        {session.status === 'failed'
          ? 'Lần lập kế hoạch trước không thành công. Bạn có thể thử lại.'
          : 'Tài liệu của phiên vừa thay đổi, cần lập lại kế hoạch.'}
      </p>
      {error && <Notice title="Không lập được kế hoạch">{error}</Notice>}
      <Button onClick={prepare} disabled={busy}>
        {busy ? 'Đang lập kế hoạch…' : 'Lập kế hoạch'}
      </Button>
    </Card>
  )
}

function ReadyView({ session, onChange }: { session: SessionView; onChange: (s: SessionView) => void }) {
  const [starting, setStarting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function start() {
    setStarting(true)
    setError(null)
    try {
      onChange(await api.startInterview(session.id))
    } catch (err) {
      setError(errorMessage(err))
      setStarting(false)
    }
  }

  return (
    <div className="space-y-5">
      <PlanPreviewCard session={session} />
      {error && <Notice title="Không bắt đầu được">{error}</Notice>}
      {!api.supportsLiveInterview && (
        <Notice title="Phỏng vấn trực tiếp sắp có" tone="sky">
          Kế hoạch trên đã được lập thật từ thư viện câu hỏi. Phần hỏi đáp với AI đang được phát
          triển ở bước tiếp theo.
        </Notice>
      )}
      <div className="flex flex-wrap gap-3">
        <Button
          onClick={start}
          disabled={starting || !api.supportsLiveInterview}
          className="px-6 py-3 text-base"
        >
          {starting ? 'Đang bắt đầu…' : 'Bắt đầu phỏng vấn'}
        </Button>
        <Link to="/" className="inline-flex items-center px-3 text-sm text-slate-600 hover:underline">
          Chọn lại thiết lập
        </Link>
      </div>
    </div>
  )
}

const AUTOPLAY_KEY = 'intervai.readQuestions'

function readAutoplayPreference(): boolean {
  try {
    return localStorage.getItem(AUTOPLAY_KEY) !== 'off'
  } catch {
    return true
  }
}

function LiveView({ session, onChange }: { session: SessionView; onChange: (s: SessionView) => void }) {
  const [answer, setAnswer] = useState('')
  const [answerMode, setAnswerMode] = useState<'text' | 'voice'>('text')
  const [busy, setBusy] = useState<'answer' | 'finish' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [speech, setSpeech] = useState<SpeechCapabilities | null>(null)
  const [autoplay, setAutoplay] = useState(readAutoplayPreference)
  const lastAttempt = useRef<{ key: string; requestId: string } | null>(null)

  const plan = session.plan_preview
  const skillTitles = useMemo(
    () => new Map(plan?.skills.map((skill) => [skill.id, skill.title]) ?? []),
    [plan],
  )
  const current = session.turns.at(-1)
  const pending = current && current.answer_text === null ? current : undefined
  const answered = pending ? session.turns.slice(0, -1) : session.turns
  const mainAsked = session.turns.filter((turn) => turn.kind === 'main').length

  useEffect(() => {
    let active = true
    api.speechCapabilities().then(
      (caps) => {
        if (active) setSpeech(caps)
      },
      () => {
        if (active) setSpeech({ stt: false, tts: false, tts_provider: null })
      },
    )
    return () => {
      active = false
    }
  }, [])

  const voice = useQuestionVoice({
    sessionId: session.id,
    turnNo: pending?.turn_no,
    text: pending?.question_text,
    autoplay: autoplay && speech !== null,
    serverTts: Boolean(speech?.tts),
  })

  const onRecorded = useCallback(
    async (wav: Blob) => {
      const { text } = await api.transcribe(session.id, wav)
      setAnswer((previous) => (previous.trim() ? `${previous.trim()} ${text}` : text))
      setAnswerMode('voice')
    },
    [session.id],
  )
  const recorder = useRecorder(onRecorded)
  const canRecord = recorder.supported && Boolean(speech?.stt)

  function toggleAutoplay() {
    const next = !autoplay
    setAutoplay(next)
    if (!next) voice.stop()
    try {
      localStorage.setItem(AUTOPLAY_KEY, next ? 'on' : 'off')
    } catch {
      // preference only
    }
  }

  function startRecording() {
    voice.stop()
    void recorder.start()
  }

  async function submit() {
    const text = answer.trim()
    if (!pending || !text || busy) return
    // Reuse the idempotency key when retrying the exact same answer after a failure.
    const key = `${pending.turn_no}:${text}`
    if (lastAttempt.current?.key !== key) lastAttempt.current = { key, requestId: crypto.randomUUID() }
    setBusy('answer')
    setError(null)
    try {
      const next = await api.submitAnswer(session.id, {
        request_id: lastAttempt.current.requestId,
        turn_no: pending.turn_no,
        answer_text: text,
        answer_mode: answerMode,
      })
      lastAttempt.current = null
      setAnswer('')
      setAnswerMode('text')
      onChange(next)
    } catch (err) {
      setError(errorMessage(err))
      // 409: the question moved on or another submission is in flight — show the latest state.
      if (err instanceof ApiError && err.status === 409) {
        try {
          onChange(await api.getInterview(session.id))
        } catch {
          // keep the current view; the error is already shown
        }
      }
    } finally {
      setBusy(null)
    }
  }

  async function finishEarly() {
    if (!window.confirm('Kết thúc phỏng vấn ngay? Các câu đã trả lời vẫn được lưu lại.')) return
    setBusy('finish')
    setError(null)
    try {
      onChange(await api.finishInterview(session.id))
    } catch (err) {
      setError(errorMessage(err))
      setBusy(null)
    }
  }

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
      event.preventDefault()
      void submit()
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2 text-sm text-slate-600">
          <Badge tone="indigo">
            Câu chính {mainAsked}/{plan?.main_questions ?? '?'}
          </Badge>
          <Badge>
            Lượt {session.turns.length}/{plan?.max_turns ?? '?'}
          </Badge>
        </div>
        <Button variant="danger" onClick={finishEarly} disabled={busy !== null}>
          {busy === 'finish' ? 'Đang kết thúc…' : 'Kết thúc sớm'}
        </Button>
      </div>

      {answered.length > 0 && (
        <Card>
          <Transcript turns={answered} skillTitles={skillTitles} />
        </Card>
      )}

      {pending && (
        <Card className="ring-2 ring-indigo-200">
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={pending.kind === 'main' ? 'indigo' : 'sky'}>{TURN_KIND_LABELS[pending.kind]}</Badge>
              <span>{skillTitles.get(pending.skill_id) ?? pending.skill_id}</span>
            </div>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => (voice.speaking ? voice.stop() : void voice.speak())}
                className="font-medium text-indigo-600 hover:underline"
              >
                {voice.speaking ? '⏹ Dừng đọc' : '🔊 Nghe câu hỏi'}
              </button>
              <label className="flex cursor-pointer items-center gap-1">
                <input type="checkbox" checked={autoplay} onChange={toggleAutoplay} />
                Tự đọc câu hỏi
              </label>
            </div>
          </div>
          <p className="mt-3 text-lg font-medium text-slate-900">{pending.question_text}</p>

          <label htmlFor="answer" className="sr-only">
            Câu trả lời
          </label>
          <textarea
            id="answer"
            value={answer}
            onChange={(event) => setAnswer(event.target.value.slice(0, MAX_ANSWER_CHARS))}
            onKeyDown={onKeyDown}
            rows={6}
            autoFocus
            disabled={busy !== null || recorder.status !== 'idle'}
            placeholder={
              canRecord
                ? 'Bấm Ghi âm để trả lời bằng giọng nói, hoặc gõ câu trả lời… (Ctrl + Enter để gửi)'
                : 'Nhập câu trả lời của bạn… (Ctrl + Enter để gửi)'
            }
            className="mt-4 w-full rounded-lg border-0 px-3 py-2 text-sm ring-1 ring-slate-300 focus:ring-2 focus:ring-indigo-500 disabled:bg-slate-50"
          />
          {answerMode === 'voice' && recorder.status === 'idle' && (
            <p className="mt-1 text-xs text-sky-700">
              Đây là transcript từ giọng nói — hãy kiểm tra và sửa thuật ngữ bị nhận sai trước khi gửi.
            </p>
          )}
          {recorder.error && (
            <div className="mt-3">
              <Notice title="Ghi âm không thành công" tone="amber">
                {recorder.error}
              </Notice>
            </div>
          )}
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
            {recorder.status === 'recording' ? (
              <Button variant="danger" onClick={recorder.stop}>
                <span className="size-2 animate-pulse rounded-full bg-rose-600" />
                Dừng · {formatSeconds(recorder.seconds)} / {formatSeconds(MAX_RECORDING_SECONDS)}
              </Button>
            ) : (
              <Button
                variant="secondary"
                onClick={startRecording}
                disabled={!canRecord || busy !== null || recorder.status === 'processing'}
                title={
                  canRecord
                    ? 'Ghi âm câu trả lời'
                    : 'Nhận dạng giọng nói chưa sẵn sàng trên máy chủ hoặc trình duyệt này'
                }
              >
                {recorder.status === 'processing' ? 'Đang nhận dạng…' : '🎙 Ghi âm'}
              </Button>
            )}
            <div className="flex items-center gap-3">
              <span className="text-xs text-slate-500">
                {answer.length}/{MAX_ANSWER_CHARS}
              </span>
              <Button onClick={submit} disabled={!answer.trim() || busy !== null}>
                {busy === 'answer' ? 'AI đang đọc câu trả lời…' : 'Gửi câu trả lời'}
              </Button>
            </div>
          </div>
          {error && (
            <div className="mt-3">
              <Notice title="Gửi không thành công">
                {error} Câu trả lời vẫn được giữ — bấm gửi lại để thử tiếp.
              </Notice>
            </div>
          )}
        </Card>
      )}
    </div>
  )
}

function CompletedView({ session }: { session: SessionView }) {
  const navigate = useNavigate()
  const hasReport = api.supportsReport && session.report_status !== null
  return (
    <Card className="text-center">
      <p className="text-4xl">🎉</p>
      <h1 className="mt-3 text-xl font-semibold">Bạn đã hoàn thành buổi phỏng vấn</h1>
      <p className="mt-2 text-sm text-slate-600">
        {session.turns.filter((t) => t.answer_text !== null).length} lượt trả lời đã được ghi nhận.
      </p>
      <p className="mx-auto mt-3 max-w-md text-sm text-slate-500">
        {hasReport
          ? 'AI đang chấm từng câu theo rubric, mọi nhận xét đều kèm trích dẫn từ câu trả lời của bạn.'
          : 'Buổi này không có câu trả lời nào để chấm. Bạn vẫn có thể xem lại transcript.'}
      </p>
      <div className="mt-5 flex justify-center gap-3">
        {hasReport ? (
          <Button onClick={() => navigate(`/interviews/${session.id}/report`)}>Xem báo cáo</Button>
        ) : (
          <Button onClick={() => navigate(`/history/${session.id}`)}>Xem transcript</Button>
        )}
        <Button variant="secondary" onClick={() => navigate('/')}>
          Phỏng vấn mới
        </Button>
      </div>
    </Card>
  )
}
