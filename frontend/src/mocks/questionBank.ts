import type { Role } from '../api/types'

// Mock-mode content only. Real questions come from the Playbook Library via the planner.

export interface MockQuestion {
  skillId: string
  text: string
  followUp: string
}

export const SKILL_TITLES: Record<string, string> = {
  machine_learning: 'Machine Learning',
  rag_systems: 'RAG Systems',
  llm_agents: 'LLM Agents',
  model_evaluation: 'Model Evaluation',
  api_design: 'API Design',
  databases: 'Databases',
  system_design: 'System Design',
  programming_fundamentals: 'Programming Fundamentals',
  sql: 'SQL',
  etl_pipeline: 'ETL Pipeline',
  data_processing: 'Data Processing',
}

// Ordered so that the first 3 (demo) cover 2 skills and all 6 (standard) cover 3–4 skills.
export const QUESTION_BANK: Record<Role, MockQuestion[]> = {
  ai_engineer: [
    {
      skillId: 'machine_learning',
      text: 'Overfitting là gì, và bạn phát hiện nó bằng cách nào?',
      followUp: 'Nếu dữ liệu chỉ có vài trăm mẫu, bạn chia tập đánh giá thế nào cho đáng tin?',
    },
    {
      skillId: 'rag_systems',
      text: 'Tìm kiếm theo từ khóa và tìm kiếm theo embedding khác nhau thế nào?',
      followUp: 'Với truy vấn chứa mã lỗi như "ERR_504", cách nào cho kết quả tốt hơn và vì sao?',
    },
    {
      skillId: 'rag_systems',
      text: 'Chatbot RAG trả lời sai một câu hỏi. Bạn tìm nguyên nhân thế nào?',
      followUp: 'Bạn đo chất lượng của bước retrieval bằng chỉ số nào?',
    },
    {
      skillId: 'llm_agents',
      text: 'Một LLM agent biết gọi tool khác gì một chuỗi prompt cố định?',
      followUp: 'Làm sao ngăn agent lặp vô hạn hoặc gọi sai tool?',
    },
    {
      skillId: 'model_evaluation',
      text: 'Khi dữ liệu mất cân bằng, vì sao accuracy có thể gây hiểu lầm?',
      followUp: 'Bạn chọn ngưỡng phân loại dựa trên những yếu tố nào?',
    },
    {
      skillId: 'model_evaluation',
      text: 'Bạn đánh giá chất lượng một ứng dụng LLM trước khi phát hành như thế nào?',
      followUp: 'Dùng LLM-as-judge có rủi ro gì và bạn kiểm soát ra sao?',
    },
  ],
  backend_developer: [
    {
      skillId: 'api_design',
      text: 'PUT và PATCH khác nhau thế nào? Khi nào một API cần idempotent?',
      followUp:
        'Client gửi lại request thanh toán do timeout. Bạn tránh trừ tiền hai lần như thế nào?',
    },
    {
      skillId: 'databases',
      text: 'Index giúp truy vấn nhanh hơn như thế nào, và khi nào index lại gây hại?',
      followUp: 'Bạn kiểm tra một truy vấn có dùng index hay không bằng cách nào?',
    },
    {
      skillId: 'databases',
      text: 'Transaction và các mức isolation giải quyết vấn đề gì?',
      followUp: 'Cho một ví dụ lỗi sẽ xảy ra nếu không dùng transaction.',
    },
    {
      skillId: 'programming_fundamentals',
      text: 'Xử lý bất đồng bộ (async) khác đa luồng thế nào trong một backend service?',
      followUp: 'Một tác vụ nặng CPU đặt trong hàm async sẽ gây ra vấn đề gì?',
    },
    {
      skillId: 'system_design',
      text: 'Bạn dùng cache thế nào để giảm tải database, và xử lý dữ liệu cũ ra sao?',
      followUp: 'Khi nhiều cache key hết hạn cùng lúc thì chuyện gì xảy ra?',
    },
    {
      skillId: 'api_design',
      text: 'Bạn thiết kế phân trang cho một API trả về danh sách rất lớn thế nào?',
      followUp: 'Cursor pagination có nhược điểm gì so với offset?',
    },
  ],
  data_engineer: [
    {
      skillId: 'sql',
      text: 'Phân biệt WHERE và HAVING, và cho một ví dụ cần dùng HAVING.',
      followUp: 'Điều kiện lọc theo thời gian nên đặt ở WHERE hay HAVING, vì sao?',
    },
    {
      skillId: 'etl_pipeline',
      text: 'Job nạp dữ liệu chạy lại sau khi lỗi giữa chừng. Bạn tránh trùng dữ liệu thế nào?',
      followUp: 'Một pipeline "idempotent" nghĩa là gì?',
    },
    {
      skillId: 'sql',
      text: 'Window function khác GROUP BY ở điểm nào? Cho một ví dụ.',
      followUp: 'Bạn tính doanh thu lũy kế theo ngày bằng window function thế nào?',
    },
    {
      skillId: 'data_processing',
      text: 'Khi nào nên dùng Spark thay vì pandas?',
      followUp: 'Data skew là gì và ảnh hưởng thế nào tới một job Spark?',
    },
    {
      skillId: 'etl_pipeline',
      text: 'Batch và streaming khác nhau thế nào, khi nào bạn chọn cách nào?',
      followUp: 'Dữ liệu đến muộn được xử lý ra sao?',
    },
    {
      skillId: 'data_processing',
      text: 'Bạn partition một bảng sự kiện rất lớn theo cột nào, và vì sao?',
      followUp: 'Quá nhiều file nhỏ gây ra vấn đề gì?',
    },
  ],
}

export const CV_OPENING_QUESTION =
  'Hãy giới thiệu một dự án trong CV mà bạn tâm đắc nhất: bài toán, vai trò của bạn và kết quả đạt được.'
