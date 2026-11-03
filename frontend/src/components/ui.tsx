import type { ButtonHTMLAttributes, ReactNode } from 'react'

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'

const BUTTON_STYLES: Record<ButtonVariant, string> = {
  primary: 'bg-indigo-600 text-white hover:bg-indigo-700 disabled:bg-indigo-300',
  secondary:
    'bg-white text-slate-800 ring-1 ring-slate-300 hover:bg-slate-50 disabled:text-slate-400',
  ghost: 'text-slate-600 hover:bg-slate-100 disabled:text-slate-300',
  danger: 'bg-white text-rose-700 ring-1 ring-rose-200 hover:bg-rose-50 disabled:text-rose-300',
}

export function Button({
  variant = 'primary',
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }) {
  return (
    <button
      type="button"
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:cursor-not-allowed ${BUTTON_STYLES[variant]} ${className}`}
      {...props}
    />
  )
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200 sm:p-6 ${className}`}>
      {children}
    </section>
  )
}

type Tone = 'slate' | 'indigo' | 'emerald' | 'amber' | 'rose' | 'sky'

const TONES: Record<Tone, string> = {
  slate: 'bg-slate-100 text-slate-700',
  indigo: 'bg-indigo-50 text-indigo-700',
  emerald: 'bg-emerald-50 text-emerald-700',
  amber: 'bg-amber-50 text-amber-800',
  rose: 'bg-rose-50 text-rose-700',
  sky: 'bg-sky-50 text-sky-700',
}

export function Badge({ children, tone = 'slate' }: { children: ReactNode; tone?: Tone }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${TONES[tone]}`}>
      {children}
    </span>
  )
}

export function Spinner({ label = 'Đang tải…' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-16 text-sm text-slate-500" role="status">
      <span className="size-5 animate-spin rounded-full border-2 border-slate-300 border-t-indigo-600" />
      {label}
    </div>
  )
}

export function Notice({
  title,
  children,
  tone = 'rose',
}: {
  title: string
  children?: ReactNode
  tone?: 'rose' | 'amber' | 'sky'
}) {
  const styles = {
    rose: 'bg-rose-50 text-rose-800 ring-rose-200',
    amber: 'bg-amber-50 text-amber-900 ring-amber-200',
    sky: 'bg-sky-50 text-sky-900 ring-sky-200',
  }[tone]
  return (
    <div className={`rounded-xl px-4 py-3 text-sm ring-1 ${styles}`} role={tone === 'rose' ? 'alert' : 'note'}>
      <p className="font-semibold">{title}</p>
      {children && <div className="mt-1">{children}</div>}
    </div>
  )
}

function scoreTone(score: number | null): Tone {
  if (score === null) return 'slate'
  if (score >= 4) return 'emerald'
  if (score >= 3) return 'amber'
  return 'rose'
}

export function ScoreBadge({ score, max = 5 }: { score: number | null; max?: number }) {
  return (
    <Badge tone={scoreTone(score)}>
      {score === null ? 'Chưa đủ dữ liệu' : `${score.toFixed(score % 1 === 0 ? 0 : 2)}/${max}`}
    </Badge>
  )
}

const BAR_COLORS: Record<Tone, string> = {
  slate: 'bg-slate-300',
  indigo: 'bg-indigo-500',
  emerald: 'bg-emerald-500',
  amber: 'bg-amber-500',
  rose: 'bg-rose-500',
  sky: 'bg-sky-500',
}

export function ScoreBar({ score }: { score: number | null }) {
  const width = score === null ? 0 : (score / 5) * 100
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
      <div className={`h-full rounded-full ${BAR_COLORS[scoreTone(score)]}`} style={{ width: `${width}%` }} />
    </div>
  )
}
