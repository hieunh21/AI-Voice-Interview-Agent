import { useEffect, useState } from 'react'
import { API_BASE_URL } from '../api'

type Status = { state: 'checking' } | { state: 'online'; version: string } | { state: 'offline' }

const HEALTH_TIMEOUT_MS = 4000

/** Pings GET /api/health once so the footer shows whether the FastAPI backend is reachable. */
export function BackendStatus() {
  const [status, setStatus] = useState<Status>({ state: 'checking' })

  useEffect(() => {
    let cancelled = false
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), HEALTH_TIMEOUT_MS)
    fetch(`${API_BASE_URL}/api/health`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const body = (await response.json()) as { version: string }
        if (!cancelled) setStatus({ state: 'online', version: body.version })
      })
      .catch(() => {
        if (!cancelled) setStatus({ state: 'offline' })
      })
      .finally(() => clearTimeout(timeout))
    return () => {
      cancelled = true
      clearTimeout(timeout)
      controller.abort()
    }
  }, [])

  const dot = { checking: 'bg-slate-300', online: 'bg-emerald-500', offline: 'bg-rose-400' }[
    status.state
  ]
  const text =
    status.state === 'online'
      ? `API online · v${status.version}`
      : status.state === 'offline'
        ? 'API offline'
        : 'Đang kiểm tra API…'

  return (
    <span className="inline-flex items-center gap-2" title={API_BASE_URL}>
      <span className={`size-2 rounded-full ${dot}`} />
      {text}
    </span>
  )
}
