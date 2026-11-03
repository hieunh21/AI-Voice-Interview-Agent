import { Link, useParams } from 'react-router'
import { api } from '../api'
import type { CriterionScore, EvaluationResult, SessionView } from '../api/types'
import { Badge, Card, Notice, ScoreBadge, ScoreBar, Spinner } from '../components/ui'
import {
  CRITERION_LABELS,
  CROSS_CUTTING_LABELS,
  REPORT_STATUS_LABELS,
  formatDateTime,
  formatScore,
  levelLabel,
  modeLabel,
  roleLabel,
} from '../lib/labels'
import { useLoader } from '../lib/useLoader'

const loadReport = async (id: string) => {
  const [session, report] = await Promise.all([api.getInterview(id), api.getReport(id)])
  return { session, report }
}

export default function ReportPage() {
  const { id = '' } = useParams()
  const { data, error, loading } = useLoader(id, loadReport)

  if (loading) return <Spinner label="Đang tải báo cáo…" />
  if (error || !data) return <Notice title="Không mở được báo cáo">{error}</Notice>

  const { session, report: response } = data
  const report = response.report
  if (response.status !== 'completed' || !report) {
    return (
      <Notice title={REPORT_STATUS_LABELS[response.status]} tone="sky">
        Báo cáo sẽ hiển thị khi chấm điểm xong.
      </Notice>
    )
  }

  const skillTitles = new Map(session.plan_preview?.skills.map((s) => [s.id, s.title]) ?? [])
  const questionText = (questionId: string) =>
    session.turns.find((t) => t.question_id === questionId)?.question_text ?? questionId

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm text-slate-500">
            Báo cáo · {formatDateTime(report.generated_at)}
          </p>
          <h1 className="text-2xl font-bold">
            {roleLabel(report.role)} · {levelLabel(report.level)}
          </h1>
          <p className="text-sm text-slate-500">{modeLabel(report.mode)}</p>
        </div>
        <Link to={`/history/${session.id}`} className="text-sm text-indigo-600 hover:underline">
          Xem transcript đầy đủ →
        </Link>
      </div>

      <Notice title="Công cụ luyện tập" tone="sky">
        {report.disclaimer}
      </Notice>

      <div className="grid gap-5 md:grid-cols-3">
        <Card className="flex flex-col items-center justify-center text-center">
          <p className="text-sm text-slate-500">Điểm kỹ thuật tổng</p>
          <p className="mt-1 text-5xl font-bold">{formatScore(report.overall_score)}</p>
          <p className="text-sm text-slate-400">/ 5</p>
        </Card>
        <Card className="md:col-span-2">
          <h2 className="font-semibold">Theo kỹ năng</h2>
          <ul className="mt-4 space-y-4">
            {report.skill_scores.map((skill) => (
              <li key={skill.skill_id}>
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium">{skillTitles.get(skill.skill_id) ?? skill.skill_id}</span>
                  <ScoreBadge score={skill.score} />
                </div>
                <div className="mt-2">
                  <ScoreBar score={skill.score} />
                </div>
                {skill.summary && <p className="mt-1 text-xs text-slate-500">{skill.summary}</p>}
              </li>
            ))}
          </ul>
        </Card>
      </div>

      {(report.top_strengths.length > 0 || report.priority_improvements.length > 0) && (
        <div className="grid gap-5 md:grid-cols-2">
          <Card>
            <h2 className="font-semibold text-emerald-700">Điểm mạnh</h2>
            <List items={report.top_strengths} />
          </Card>
          <Card>
            <h2 className="font-semibold text-amber-700">Cần cải thiện trước</h2>
            <List items={report.priority_improvements} />
            {report.study_topics.length > 0 && (
              <>
                <h3 className="mt-4 text-sm font-semibold text-slate-700">Chủ đề nên ôn</h3>
                <div className="mt-2 flex flex-wrap gap-2">
                  {report.study_topics.map((topic) => (
                    <Badge key={topic} tone="indigo">
                      {topic}
                    </Badge>
                  ))}
                </div>
              </>
            )}
          </Card>
        </div>
      )}

      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Từng câu hỏi</h2>
        {report.questions.map((result, index) => (
          <QuestionCard
            key={result.question_id}
            index={index + 1}
            result={result}
            question={questionText(result.question_id)}
            skillTitle={skillTitles.get(result.skill_id) ?? result.skill_id}
            session={session}
          />
        ))}
      </section>

      {report.cross_cutting.length > 0 && (
        <Card>
          <h2 className="font-semibold">Kỹ năng chung (chấm trên toàn bộ buổi)</h2>
          <div className="mt-4 grid gap-5 md:grid-cols-2">
            {report.cross_cutting.map((skill) => (
              <div key={skill.skill_id}>
                <h3 className="text-sm font-semibold text-slate-700">
                  {CROSS_CUTTING_LABELS[skill.skill_id] ?? skill.skill_id}
                </h3>
                <CriteriaList criteria={skill.criteria} />
                {skill.summary && <p className="mt-2 text-xs text-slate-500">{skill.summary}</p>}
              </div>
            ))}
          </div>
        </Card>
      )}

      <p className="text-xs text-slate-400">
        Rubric v{report.versions.rubric} · Evaluator prompt v{report.versions.evaluator_prompt}
      </p>
    </div>
  )
}

function List({ items }: { items: string[] }) {
  if (items.length === 0) return <p className="mt-2 text-sm text-slate-500">—</p>
  return (
    <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  )
}

function CriteriaList({ criteria }: { criteria: CriterionScore[] }) {
  return (
    <ul className="mt-3 space-y-3">
      {criteria.map((criterion) => (
        <li key={criterion.criterion_id} className="text-sm">
          <div className="flex items-center justify-between gap-2">
            <span>{CRITERION_LABELS[criterion.criterion_id] ?? criterion.criterion_id}</span>
            <ScoreBadge score={criterion.score} />
          </div>
          <p className="mt-1 text-xs text-slate-500">{criterion.rationale}</p>
          {criterion.evidence.map((evidence) => (
            <blockquote
              key={`${evidence.turn_no}-${evidence.quote}`}
              className="mt-1 border-l-2 border-indigo-200 pl-3 text-xs text-slate-600 italic"
            >
              “{evidence.quote}” <span className="not-italic text-slate-400">— lượt #{evidence.turn_no}</span>
            </blockquote>
          ))}
        </li>
      ))}
    </ul>
  )
}

function QuestionCard({
  index,
  result,
  question,
  skillTitle,
  session,
}: {
  index: number
  result: EvaluationResult
  question: string
  skillTitle: string
  session: SessionView
}) {
  const followUps = session.turns.filter((t) => t.parent_question_id === result.question_id).length
  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs text-slate-500">
            Câu {index} · {skillTitle}
            {followUps > 0 && ` · ${followUps} câu hỏi sâu`}
          </p>
          <h3 className="mt-1 font-medium">{question}</h3>
        </div>
        <ScoreBadge score={result.weighted_score} />
      </div>

      {result.status === 'insufficient_evidence' && (
        <div className="mt-4">
          <Notice title="Chưa đủ bằng chứng để chấm" tone="amber">
            Transcript của câu này không đủ nội dung — câu hỏi không được tính vào điểm tổng.
          </Notice>
        </div>
      )}

      {result.status === 'scored' && <CriteriaList criteria={result.criteria} />}

      {(result.covered_points.length > 0 || result.missed_points.length > 0) && (
        <div className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
          <div>
            <p className="font-medium text-emerald-700">Đã nêu được</p>
            <List items={result.covered_points} />
          </div>
          <div>
            <p className="font-medium text-amber-700">Còn thiếu</p>
            <List items={result.missed_points} />
          </div>
        </div>
      )}

      {result.improvement_suggestion && (
        <p className="mt-4 rounded-lg bg-indigo-50 px-3 py-2 text-sm text-indigo-900">
          💡 {result.improvement_suggestion}
        </p>
      )}
    </Card>
  )
}
