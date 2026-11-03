import { Link } from 'react-router'
import { api } from '../api'
import type { SessionSummary } from '../api/types'
import { Badge, Card, Notice, ScoreBadge, Spinner } from '../components/ui'
import {
  SESSION_STATUS_LABELS,
  formatDateTime,
  levelLabel,
  modeLabel,
  roleLabel,
} from '../lib/labels'
import { useLoader } from '../lib/useLoader'

const loadSessions = () => api.listInterviews()

export default function HistoryPage() {
  const { data: sessions, error, loading } = useLoader('all', loadSessions)

  if (loading) return <Spinner />
  if (error || !sessions) return <Notice title="Không tải được lịch sử">{error}</Notice>

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold">Lịch sử phỏng vấn</h1>
      {sessions.length === 0 ? (
        <Card className="text-center">
          <p className="text-slate-600">Bạn chưa có buổi phỏng vấn nào.</p>
          <Link to="/" className="mt-3 inline-block text-sm font-medium text-indigo-600 hover:underline">
            Bắt đầu buổi đầu tiên →
          </Link>
        </Card>
      ) : (
        <ul className="space-y-3">
          {sessions.map((session) => (
            <SessionRow key={session.id} session={session} />
          ))}
        </ul>
      )}
    </div>
  )
}

function SessionRow({ session }: { session: SessionSummary }) {
  const action =
    session.status === 'completed' && session.report_status === 'completed'
      ? { to: `/interviews/${session.id}/report`, label: 'Xem báo cáo' }
      : ['ready', 'in_progress', 'created', 'failed'].includes(session.status)
        ? { to: `/interviews/${session.id}`, label: 'Tiếp tục' }
        : null

  return (
    <li>
      <Card className="flex flex-wrap items-center justify-between gap-4 !p-4">
        <div className="min-w-0">
          <p className="font-semibold">
            {roleLabel(session.role)} · {levelLabel(session.level)}
          </p>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
            <span>{formatDateTime(session.created_at)}</span>
            <Badge>{modeLabel(session.mode)}</Badge>
            <Badge tone={session.status === 'completed' ? 'emerald' : 'amber'}>
              {SESSION_STATUS_LABELS[session.status]}
            </Badge>
            {session.has_cv && <Badge tone="sky">CV</Badge>}
            {session.has_jd && <Badge tone="sky">JD</Badge>}
            {!session.has_cv && !session.has_jd && <Badge>Không tài liệu</Badge>}
          </div>
        </div>
        <div className="flex items-center gap-3">
          {session.overall_score !== null && <ScoreBadge score={session.overall_score} />}
          <Link to={`/history/${session.id}`} className="text-sm text-slate-600 hover:underline">
            Chi tiết
          </Link>
          {action && (
            <Link
              to={action.to}
              className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"
            >
              {action.label}
            </Link>
          )}
        </div>
      </Card>
    </li>
  )
}
