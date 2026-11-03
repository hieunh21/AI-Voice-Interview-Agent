import { BrowserRouter, Route, Routes } from 'react-router'
import { Layout } from './components/Layout'
import HistoryPage from './pages/HistoryPage'
import InterviewRoomPage from './pages/InterviewRoomPage'
import NotFoundPage from './pages/NotFoundPage'
import ReportPage from './pages/ReportPage'
import SessionDetailPage from './pages/SessionDetailPage'
import SetupPage from './pages/SetupPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<SetupPage />} />
          <Route path="interviews/:id" element={<InterviewRoomPage />} />
          <Route path="interviews/:id/report" element={<ReportPage />} />
          <Route path="history" element={<HistoryPage />} />
          <Route path="history/:id" element={<SessionDetailPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
