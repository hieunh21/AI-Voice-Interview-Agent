import type { SessionView } from '../api/types'
import { INPUT_SOURCE_LABELS, levelLabel, modeLabel, roleLabel } from '../lib/labels'
import { Badge, Card, Notice } from './ui'

export function PlanPreviewCard({ session }: { session: SessionView }) {
  const plan = session.plan_preview
  if (!plan) return <Notice title="Kế hoạch phỏng vấn chưa sẵn sàng." tone="amber" />

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm text-slate-500">Kế hoạch phỏng vấn</p>
          <h2 className="text-xl font-semibold">
            {roleLabel(session.role)} · {levelLabel(session.level)}
          </h2>
        </div>
        <Badge tone="indigo">{modeLabel(session.mode)}</Badge>
      </div>

      <dl className="mt-5 grid grid-cols-3 gap-3 text-center">
        <div className="rounded-xl bg-slate-50 p-3">
          <dt className="text-xs text-slate-500">Câu hỏi chính</dt>
          <dd className="text-2xl font-semibold">{plan.main_questions}</dd>
        </div>
        <div className="rounded-xl bg-slate-50 p-3">
          <dt className="text-xs text-slate-500">Tối đa lượt</dt>
          <dd className="text-2xl font-semibold">{plan.max_turns}</dd>
        </div>
        <div className="rounded-xl bg-slate-50 p-3">
          <dt className="text-xs text-slate-500">Thời lượng</dt>
          <dd className="text-2xl font-semibold">~{plan.time_budget_minutes}′</dd>
        </div>
      </dl>

      <h3 className="mt-6 text-sm font-semibold text-slate-700">Chủ đề sẽ được hỏi</h3>
      <ul className="mt-2 divide-y divide-slate-100">
        {plan.skills.map((skill) => (
          <li key={skill.id} className="flex items-center justify-between gap-3 py-2 text-sm">
            <span className="flex items-center gap-2">
              {skill.title}
              {skill.is_core && <Badge tone="emerald">Cốt lõi</Badge>}
            </span>
            <span className="text-slate-500">{skill.target_questions} câu</span>
          </li>
        ))}
      </ul>

      <div className="mt-5 flex flex-wrap items-center gap-2 text-xs text-slate-500">
        Nguồn:
        {plan.input_sources.map((source) => (
          <Badge key={source} tone={source === 'cv' || source === 'jd' ? 'sky' : 'slate'}>
            {INPUT_SOURCE_LABELS[source]}
          </Badge>
        ))}
      </div>

      {plan.warnings.length > 0 && (
        <div className="mt-4">
          <Notice title="Lưu ý" tone="amber">
            <ul className="list-disc space-y-1 pl-5">
              {plan.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </Notice>
        </div>
      )}
    </Card>
  )
}
