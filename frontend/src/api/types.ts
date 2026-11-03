// Mirrors the backend contracts (ai/schemas, backend/app/schemas). Field names stay snake_case
// because they are the wire format. The mock fixtures are validated against the Pydantic models
// by tests/unit/test_frontend_fixtures.py, so drift is caught in CI.

export type Role = 'ai_engineer' | 'backend_developer' | 'data_engineer'
export type Level = 'intern' | 'fresher' | 'junior'
export type InterviewMode = 'demo' | 'standard'
export type SessionStatus =
  | 'created'
  | 'preparing'
  | 'ready'
  | 'in_progress'
  | 'completed'
  | 'failed'
export type EndReason = 'plan_completed' | 'user_ended' | 'max_turns' | 'time_budget'
export type TurnKind = 'main' | 'follow_up' | 'clarify'
export type ReportStatus = 'pending' | 'processing' | 'completed' | 'failed'
export type EvaluationStatus = 'scored' | 'insufficient_evidence'
export type InputSource = 'role_config' | 'role_playbook' | 'competency_skills' | 'cv' | 'jd'

export interface InterviewSetup {
  role: Role
  level: Level
  mode: InterviewMode
  cv_text?: string
  jd_text?: string
}

export interface VersionRef {
  id: string
  version: string
}

export interface PlanPreviewSkill {
  id: string
  title: string
  version: string
  is_core: boolean
  target_questions: number
}

export interface PlanPreview {
  role_playbook: VersionRef
  skills: PlanPreviewSkill[]
  main_questions: number
  max_turns: number
  time_budget_minutes: number
  input_sources: InputSource[]
  warnings: string[]
}

export interface TurnView {
  turn_no: number
  question_id: string
  parent_question_id: string | null
  kind: TurnKind
  skill_id: string
  question_text: string
  answer_text: string | null
  asked_at: string
  answered_at: string | null
}

export interface SessionView {
  id: string
  role: Role
  level: Level
  mode: InterviewMode
  status: SessionStatus
  has_cv: boolean
  has_jd: boolean
  created_at: string
  started_at: string | null
  ended_at: string | null
  end_reason: EndReason | null
  plan_preview: PlanPreview | null
  turns: TurnView[]
  report_status: ReportStatus | null
}

export interface SessionSummary {
  id: string
  role: Role
  level: Level
  mode: InterviewMode
  status: SessionStatus
  has_cv: boolean
  has_jd: boolean
  created_at: string
  ended_at: string | null
  report_status: ReportStatus | null
  overall_score: number | null
}

export interface EvidenceQuote {
  turn_no: number
  quote: string
}

export interface CriterionScore {
  criterion_id: string
  score: number | null
  rationale: string
  evidence: EvidenceQuote[]
}

export interface EvaluationResult {
  question_id: string
  skill_id: string
  skill_version: string
  status: EvaluationStatus
  turn_nos: number[]
  criteria: CriterionScore[]
  weighted_score: number | null
  covered_points: string[]
  missed_points: string[]
  strengths: string[]
  gaps: string[]
  improvement_suggestion: string
}

export interface SkillScore {
  skill_id: string
  skill_version: string
  score: number | null
  question_ids: string[]
  summary: string
}

export interface CrossCuttingResult {
  skill_id: string
  skill_version: string
  criteria: CriterionScore[]
  summary: string
}

export interface InterviewReport {
  session_id: string
  role: Role
  level: Level
  mode: InterviewMode
  overall_score: number | null
  skill_scores: SkillScore[]
  cross_cutting: CrossCuttingResult[]
  questions: EvaluationResult[]
  top_strengths: string[]
  priority_improvements: string[]
  study_topics: string[]
  versions: { rubric: string; evaluator_prompt: string }
  disclaimer: string
  generated_at: string
}

export interface ReportResponse {
  status: ReportStatus
  report: InterviewReport | null
}

export interface AnswerSubmission {
  /** Idempotency key: retrying the same submission never creates a second turn. */
  request_id: string
  answer_text: string
}

export interface ApiClient {
  /** Create a session and prepare its plan (real API: POST /interviews then /prepare). */
  createInterview(setup: InterviewSetup): Promise<SessionView>
  getInterview(id: string): Promise<SessionView>
  listInterviews(): Promise<SessionSummary[]>
  startInterview(id: string): Promise<SessionView>
  submitAnswer(id: string, submission: AnswerSubmission): Promise<SessionView>
  finishInterview(id: string): Promise<SessionView>
  getReport(id: string): Promise<ReportResponse>
  deleteInterview(id: string): Promise<void>
}

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}
