import { useMemo, useRef, useState, type KeyboardEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { api } from '../api'
import type { SessionView } from '../api/types'
import { PlanPreviewCard } from '../components/PlanPreviewCard'
import { Transcript } from '../components/Transcript'
import { Badge, Button, Card, Notice, Spinner } from '../components/ui'
import { errorMessage } from '../lib/errors'
import { SESSION_STATUS_LABELS, TURN_KIND_LABELS } from '../lib/labels'
import { useLoader } from '../lib/useLoader'

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

function LiveView({ session, onChange }: { session: SessionView; onChange: (s: SessionView) => void }) {
  const [answer, setAnswer] = useState('')
  const [busy, setBusy] = useState<'answer' | 'finish' | null>(null)
  const [error, setError] = useState<string | null>(null)
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
        answer_text: text,
      })
      lastAttempt.current = null
      setAnswer('')
      onChange(next)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(null)
    }
  }

  async function finishEarly() {
    if (!window.confirm('Kết thúc phỏng vấn ngay? Các câu đã trả lời vẫn được chấm điểm.')) return
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
          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
            <Badge tone={pending.kind === 'main' ? 'indigo' : 'sky'}>{TURN_KIND_LABELS[pending.kind]}</Badge>
            <span>{skillTitles.get(pending.skill_id) ?? pending.skill_id}</span>
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
            disabled={busy !== null}
            placeholder="Nhập câu trả lời của bạn… (Ctrl + Enter để gửi)"
            className="mt-4 w-full rounded-lg border-0 px-3 py-2 text-sm ring-1 ring-slate-300 focus:ring-2 focus:ring-indigo-500 disabled:bg-slate-50"
          />
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
            <Button
              variant="secondary"
              disabled
              title="Trả lời bằng giọng nói sẽ có ở bản tiếp theo"
              aria-label="Trả lời bằng giọng nói (sắp có)"
            >
              🎙 Giọng nói (sắp có)
            </Button>
            <div className="flex items-center gap-3">
              <span className="text-xs text-slate-500">
                {answer.length}/{MAX_ANSWER_CHARS}
              </span>
              <Button onClick={submit} disabled={!answer.trim() || busy !== null}>
                {busy === 'answer' ? 'Đang gửi…' : 'Gửi câu trả lời'}
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
  return (
    <Card className="text-center">
      <p className="text-4xl">🎉</p>
      <h1 className="mt-3 text-xl font-semibold">Bạn đã hoàn thành buổi phỏng vấn</h1>
      <p className="mt-2 text-sm text-slate-600">
        {session.turns.filter((t) => t.answer_text !== null).length} lượt trả lời đã được ghi nhận.
      </p>
      <div className="mt-5 flex justify-center gap-3">
        <Button onClick={() => navigate(`/interviews/${session.id}/report`)}>Xem báo cáo</Button>
        <Button variant="secondary" onClick={() => navigate('/')}>
          Phỏng vấn mới
        </Button>
      </div>
    </Card>
  )
}
