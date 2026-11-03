import { useState, type ChangeEvent, type FormEvent } from 'react'
import { useNavigate } from 'react-router'
import { api } from '../api'
import { Button, Card, Notice } from '../components/ui'
import { errorMessage } from '../lib/errors'
import { LEVELS, MODES, ROLES } from '../lib/labels'
import {
  EMPTY_SETUP,
  MAX_CV_CHARS,
  MAX_JD_CHARS,
  toSetupPayload,
  validateSetup,
  type SetupErrors,
  type SetupForm,
} from '../lib/setup'

const optionClass = (selected: boolean) =>
  `cursor-pointer rounded-xl p-4 text-left ring-1 transition focus-within:ring-2 focus-within:ring-indigo-500 ${
    selected ? 'bg-indigo-50 ring-indigo-500' : 'bg-white ring-slate-200 hover:ring-slate-300'
  }`

export default function SetupPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState<SetupForm>(EMPTY_SETUP)
  const [errors, setErrors] = useState<SetupErrors>({})
  const [showDocuments, setShowDocuments] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const update = <K extends keyof SetupForm>(key: K, value: SetupForm[K]) => {
    setForm((current) => ({ ...current, [key]: value }))
    setErrors((current) => ({ ...current, [key]: undefined }))
  }

  const loadTextFile = (key: 'cvText' | 'jdText') => async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) update(key, await file.text())
    event.target.value = ''
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const found = validateSetup(form)
    setErrors(found)
    if (Object.keys(found).length > 0) return
    setSubmitting(true)
    setSubmitError(null)
    try {
      const session = await api.createInterview(toSetupPayload(form))
      navigate(`/interviews/${session.id}`)
    } catch (error) {
      setSubmitError(errorMessage(error))
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6" noValidate>
      <div>
        <h1 className="text-2xl font-bold sm:text-3xl">Luyện phỏng vấn kỹ thuật với AI</h1>
        <p className="mt-2 text-slate-600">
          Chọn vị trí và cấp độ để bắt đầu ngay. CV và JD là tùy chọn — thêm vào nếu muốn câu hỏi
          sát với bạn hơn.
        </p>
      </div>

      <Card>
        <fieldset>
          <legend className="text-base font-semibold">
            1. Vị trí ứng tuyển <span className="text-rose-600">*</span>
          </legend>
          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            {ROLES.map((role) => (
              <label key={role.value} className={optionClass(form.role === role.value)}>
                <input
                  type="radio"
                  name="role"
                  value={role.value}
                  checked={form.role === role.value}
                  onChange={() => update('role', role.value)}
                  className="sr-only"
                />
                <span className="block font-semibold">{role.label}</span>
                <span className="mt-1 block text-sm text-slate-500">{role.description}</span>
              </label>
            ))}
          </div>
          {errors.role && <p className="mt-2 text-sm text-rose-600">{errors.role}</p>}
        </fieldset>

        <fieldset className="mt-6">
          <legend className="text-base font-semibold">
            2. Cấp độ <span className="text-rose-600">*</span>
          </legend>
          <div className="mt-3 grid grid-cols-3 gap-3">
            {LEVELS.map((level) => (
              <label key={level.value} className={optionClass(form.level === level.value)}>
                <input
                  type="radio"
                  name="level"
                  value={level.value}
                  checked={form.level === level.value}
                  onChange={() => update('level', level.value)}
                  className="sr-only"
                />
                <span className="block font-semibold">{level.label}</span>
                <span className="mt-1 block text-xs text-slate-500">{level.description}</span>
              </label>
            ))}
          </div>
          {errors.level && <p className="mt-2 text-sm text-rose-600">{errors.level}</p>}
        </fieldset>

        <fieldset className="mt-6">
          <legend className="text-base font-semibold">3. Thời lượng</legend>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            {MODES.map((mode) => (
              <label key={mode.value} className={optionClass(form.mode === mode.value)}>
                <input
                  type="radio"
                  name="mode"
                  value={mode.value}
                  checked={form.mode === mode.value}
                  onChange={() => update('mode', mode.value)}
                  className="sr-only"
                />
                <span className="block font-semibold">{mode.label}</span>
                <span className="mt-1 block text-sm text-slate-500">{mode.description}</span>
              </label>
            ))}
          </div>
        </fieldset>
      </Card>

      <Card>
        <button
          type="button"
          onClick={() => setShowDocuments((open) => !open)}
          className="flex w-full items-center justify-between text-left"
          aria-expanded={showDocuments}
        >
          <span>
            <span className="block text-base font-semibold">4. Cá nhân hóa (tùy chọn)</span>
            <span className="block text-sm text-slate-500">
              Thêm CV để được hỏi về dự án của bạn, thêm JD để ưu tiên kỹ năng nhà tuyển dụng cần.
            </span>
          </span>
          <span className="text-slate-400">{showDocuments ? '−' : '+'}</span>
        </button>

        {showDocuments && (
          <div className="mt-5 grid gap-5 sm:grid-cols-2">
            {(
              [
                ['cvText', 'CV', MAX_CV_CHARS, 'Dán nội dung CV (dự án, kinh nghiệm, kỹ năng)…'],
                ['jdText', 'Job Description', MAX_JD_CHARS, 'Dán mô tả công việc…'],
              ] as const
            ).map(([key, label, max, placeholder]) => (
              <div key={key}>
                <div className="flex items-center justify-between">
                  <label htmlFor={key} className="text-sm font-medium">
                    {label}
                  </label>
                  <label className="cursor-pointer text-xs font-medium text-indigo-600 hover:underline">
                    Tải file .txt
                    <input type="file" accept=".txt,text/plain" className="sr-only" onChange={loadTextFile(key)} />
                  </label>
                </div>
                <textarea
                  id={key}
                  value={form[key]}
                  onChange={(event) => update(key, event.target.value)}
                  rows={8}
                  placeholder={placeholder}
                  className="mt-2 w-full rounded-lg border-0 px-3 py-2 text-sm ring-1 ring-slate-300 focus:ring-2 focus:ring-indigo-500"
                />
                <div className="mt-1 flex justify-between text-xs text-slate-500">
                  <span className="text-rose-600">{errors[key]}</span>
                  <span>
                    {form[key].trim().length.toLocaleString('vi-VN')}/{max.toLocaleString('vi-VN')}
                  </span>
                </div>
              </div>
            ))}
            <p className="text-xs text-slate-500 sm:col-span-2">
              Tài liệu chỉ dùng để lập kế hoạch cho phiên này và bị xóa cùng phiên. Hỗ trợ PDF sẽ có
              khi kết nối backend. Đừng dán thông tin nhạy cảm không cần thiết.
            </p>
          </div>
        )}
      </Card>

      {submitError && <Notice title="Không tạo được phiên phỏng vấn">{submitError}</Notice>}

      <div className="flex flex-col items-start gap-2 sm:flex-row sm:items-center">
        <Button type="submit" disabled={submitting} className="px-6 py-3 text-base">
          {submitting ? 'Đang lập kế hoạch…' : 'Tạo kế hoạch phỏng vấn'}
        </Button>
        <span className="text-sm text-slate-500">Không cần CV hay JD để bắt đầu.</span>
      </div>
    </form>
  )
}
