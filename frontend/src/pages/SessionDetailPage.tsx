import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { api } from '../api'
import { PlanPreviewCard } from '../components/PlanPreviewCard'
import { Transcript } from '../components/Transcript'
import { Button, Card, Notice, Spinner } from '../components/ui'
import { errorMessage } from '../lib/errors'
import { SESSION_STATUS_LABELS, formatDateTime } from '../lib/labels'
import { useLoader } from '../lib/useLoader'

const loadSession = (id: string) => api.getInterview(id)

export default function SessionDetailPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const { data: session, error, loading } = useLoader(id, loadSession)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  if (loading) return <Spinner />
  if (error || !session) return <Notice title="Không mở được phiên">{error}</Notice>

  async function remove() {
    if (!window.confirm('Xóa vĩnh viễn phiên này, transcript, CV/JD và báo cáo liên quan?')) return
    setDeleting(true)
    setDeleteError(null)
    try {
      await api.deleteInterview(id)
      navigate('/history')
    } catch (err) {
      setDeleteError(errorMessage(err))
      setDeleting(false)
    }
  }

  const skillTitles = new Map(session.plan_preview?.skills.map((s) => [s.id, s.title]) ?? [])

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link to="/history" className="text-sm text-slate-500 hover:underline">
            ← Lịch sử
          </Link>
          <p className="mt-1 text-sm text-slate-500">
            {SESSION_STATUS_LABELS[session.status]} · tạo lúc {formatDateTime(session.created_at)}
          </p>
        </div>
        <div className="flex gap-3">
          {session.report_status === 'completed' && (
            <Link
              to={`/interviews/${session.id}/report`}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
            >
              Xem báo cáo
            </Link>
          )}
          <Button variant="danger" onClick={remove} disabled={deleting}>
            {deleting ? 'Đang xóa…' : 'Xóa phiên'}
          </Button>
        </div>
      </div>

      {deleteError && <Notice title="Không xóa được phiên">{deleteError}</Notice>}

      <PlanPreviewCard session={session} />

      <Card>
        <h2 className="mb-4 font-semibold">Transcript</h2>
        <Transcript turns={session.turns} skillTitles={skillTitles} />
      </Card>

      {session.plan_preview && (
        <p className="text-xs text-slate-400">
          Role playbook {session.plan_preview.role_playbook.id} v{session.plan_preview.role_playbook.version}
          {' · '}
          {session.plan_preview.skills.map((s) => `${s.id} v${s.version}`).join(' · ')}
        </p>
      )}
    </div>
  )
}
