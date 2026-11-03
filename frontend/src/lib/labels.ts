import type {
  InputSource,
  InterviewMode,
  Level,
  ReportStatus,
  Role,
  SessionStatus,
  TurnKind,
} from '../api/types'

export const ROLES: { value: Role; label: string; description: string }[] = [
  {
    value: 'ai_engineer',
    label: 'AI Engineer',
    description: 'Machine learning, RAG, LLM agents, đánh giá mô hình.',
  },
  {
    value: 'backend_developer',
    label: 'Backend Developer',
    description: 'Thiết kế API, cơ sở dữ liệu, system design.',
  },
  {
    value: 'data_engineer',
    label: 'Data Engineer',
    description: 'SQL, ETL pipeline, xử lý dữ liệu lớn.',
  },
]

export const LEVELS: { value: Level; label: string; description: string }[] = [
  { value: 'intern', label: 'Intern', description: 'Thực tập sinh' },
  { value: 'fresher', label: 'Fresher', description: 'Dưới 1 năm kinh nghiệm' },
  { value: 'junior', label: 'Junior', description: '1–3 năm kinh nghiệm' },
]

// Kept in sync with ai/config/competency_catalog.yaml (modes).
export const MODES: {
  value: InterviewMode
  label: string
  description: string
  mainQuestions: number
  minutes: number
}[] = [
  {
    value: 'demo',
    label: 'Demo nhanh',
    description: '3 câu hỏi chính, khoảng 12 phút.',
    mainQuestions: 3,
    minutes: 12,
  },
  {
    value: 'standard',
    label: 'Tiêu chuẩn',
    description: '6 câu hỏi chính, khoảng 30 phút.',
    mainQuestions: 6,
    minutes: 30,
  },
]

export const roleLabel = (role: Role) => ROLES.find((r) => r.value === role)?.label ?? role
export const levelLabel = (level: Level) => LEVELS.find((l) => l.value === level)?.label ?? level
export const modeLabel = (mode: InterviewMode) => MODES.find((m) => m.value === mode)?.label ?? mode

export const SESSION_STATUS_LABELS: Record<SessionStatus, string> = {
  created: 'Mới tạo',
  preparing: 'Đang lập kế hoạch',
  ready: 'Sẵn sàng',
  in_progress: 'Đang phỏng vấn',
  completed: 'Đã hoàn thành',
  failed: 'Lỗi',
}

export const REPORT_STATUS_LABELS: Record<ReportStatus, string> = {
  pending: 'Đang chờ chấm',
  processing: 'Đang chấm điểm',
  completed: 'Có báo cáo',
  failed: 'Chấm điểm lỗi',
}

export const INPUT_SOURCE_LABELS: Record<InputSource, string> = {
  role_config: 'Cấu hình vị trí',
  role_playbook: 'Role playbook',
  competency_skills: 'Competency skills',
  cv: 'CV',
  jd: 'JD',
}

export const TURN_KIND_LABELS: Record<TurnKind, string> = {
  main: 'Câu hỏi',
  follow_up: 'Hỏi sâu',
  clarify: 'Làm rõ',
}

// Names from ai/config/rubric_criteria.yaml.
export const CRITERION_LABELS: Record<string, string> = {
  technical_accuracy: 'Độ chính xác kỹ thuật',
  completeness: 'Độ đầy đủ ý chính',
  reasoning: 'Lập luận và giải thích',
  practical_examples: 'Ví dụ thực tế',
  clarity: 'Diễn đạt rõ ràng',
  structure: 'Cấu trúc câu trả lời',
  decomposition: 'Phân rã vấn đề',
  handling_uncertainty: 'Xử lý khi chưa chắc chắn',
}

export const CROSS_CUTTING_LABELS: Record<string, string> = {
  communication: 'Giao tiếp',
  problem_solving: 'Giải quyết vấn đề',
}

const dateFormatter = new Intl.DateTimeFormat('vi-VN', {
  dateStyle: 'medium',
  timeStyle: 'short',
})

export const formatDateTime = (iso: string) => dateFormatter.format(new Date(iso))
export const formatScore = (score: number | null) => (score === null ? '—' : score.toFixed(1))
