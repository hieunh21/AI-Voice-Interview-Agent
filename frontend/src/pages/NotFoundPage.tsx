import { Link } from 'react-router'
import { Card } from '../components/ui'

export default function NotFoundPage() {
  return (
    <Card className="text-center">
      <h1 className="text-xl font-semibold">Không tìm thấy trang</h1>
      <Link to="/" className="mt-3 inline-block text-sm text-indigo-600 hover:underline">
        Về trang chính
      </Link>
    </Card>
  )
}
