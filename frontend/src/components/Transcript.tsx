import type { TurnView } from '../api/types'
import { TURN_KIND_LABELS } from '../lib/labels'
import { Badge } from './ui'

export function Transcript({ turns, skillTitles }: { turns: TurnView[]; skillTitles: Map<string, string> }) {
  if (turns.length === 0) {
    return <p className="text-sm text-slate-500">Chưa có lượt hỏi đáp nào.</p>
  }
  return (
    <ol className="space-y-5">
      {turns.map((turn) => (
        <li key={turn.turn_no} className="space-y-2">
          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
            <span className="font-mono">#{turn.turn_no}</span>
            <Badge tone={turn.kind === 'main' ? 'indigo' : 'sky'}>{TURN_KIND_LABELS[turn.kind]}</Badge>
            <span>{skillTitles.get(turn.skill_id) ?? turn.skill_id}</span>
          </div>
          <div className="max-w-[90%] rounded-2xl rounded-tl-sm bg-slate-100 px-4 py-3 text-sm text-slate-800">
            {turn.question_text}
          </div>
          {turn.answer_text !== null && (
            <div className="ml-auto max-w-[90%] rounded-2xl rounded-tr-sm bg-indigo-600 px-4 py-3 text-sm whitespace-pre-wrap text-white">
              {turn.answer_text}
            </div>
          )}
        </li>
      ))}
    </ol>
  )
}
