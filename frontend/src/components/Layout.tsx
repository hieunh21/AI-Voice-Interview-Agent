import { NavLink, Outlet } from 'react-router'
import { USING_MOCKS } from '../api'
import { BackendStatus } from './BackendStatus'

const navClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-lg px-3 py-2 text-sm font-medium transition ${
    isActive ? 'bg-indigo-50 text-indigo-700' : 'text-slate-600 hover:bg-slate-100'
  }`

export function Layout() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
          <NavLink to="/" className="flex items-center gap-2 font-bold text-slate-900">
            <span className="grid size-8 place-items-center rounded-lg bg-indigo-600 text-sm text-white">
              AI
            </span>
            IntervAI
          </NavLink>
          <nav className="flex items-center gap-1">
            <NavLink to="/" end className={navClass}>
              Phỏng vấn mới
            </NavLink>
            <NavLink to="/history" className={navClass}>
              Lịch sử
            </NavLink>
          </nav>
        </div>
      </header>

      {USING_MOCKS && (
        <div className="border-b border-amber-200 bg-amber-50 px-4 py-2 text-center text-xs text-amber-900">
          Chế độ mô phỏng: câu hỏi và điểm số là dữ liệu mẫu, chưa kết nối AI.
        </div>
      )}

      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">
        <Outlet />
      </main>

      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-2 px-4 py-4 text-xs text-slate-500">
          <span>IntervAI — công cụ luyện phỏng vấn, không phải đánh giá tuyển dụng chính thức.</span>
          <BackendStatus />
        </div>
      </footer>
    </div>
  )
}
