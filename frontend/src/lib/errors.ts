import { ApiError } from '../api/types'

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message
  if (error instanceof Error) return 'Đã có lỗi xảy ra. Vui lòng thử lại.'
  return 'Đã có lỗi không xác định.'
}
