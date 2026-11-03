---
id: llm_agents
kind: competency_skill
version: 1.0.1
assessment: question
levels: [intern, fresher, junior]
keywords: [llm, large language model, llm agent, ai agent, agent, agents, agentic, tool calling, function calling, langgraph, langchain, autogen, crewai, prompt engineering, openai api, gemini, mcp, workflow orchestration]
status: draft
---

# LLM Agents & Workflow Orchestration

## Learning Objectives

- Phân biệt workflow định trước với agent tự chọn hành động bằng tool calling.
- Thiết kế state, điều kiện dừng, retry và idempotency cho hệ thống có LLM.
- Kiểm soát quyền hạn, an toàn và đo lường chất lượng agent.

## Core Knowledge

- Agent gồm mục tiêu, state, các tool có schema rõ ràng, quyền hạn và điều kiện dừng; nhiều LLM hơn không có nghĩa là tốt hơn.
- Tool/function calling: mô hình chỉ sinh ra lời gọi có cấu trúc (tên tool và tham số theo schema); ứng dụng mới là bên thực thi, kiểm tra tham số và trả kết quả lại cho mô hình.
- Dùng bước xác định (deterministic) cho hành động đã rõ; dùng LLM khi cần chọn phương án từ thông tin không có cấu trúc.
- Gọi tool cần validate input/output, timeout, retry có giới hạn và chống lặp tác dụng phụ (idempotency key cho mỗi hành động logic).
- Giới hạn cứng (số bước, ngân sách, thời gian) phải do backend thực thi, không dựa vào việc nhắc trong prompt.
- LangGraph lưu state theo checkpoint để resume; khi retry phải tránh chạy lại thao tác có tác dụng phụ.
- Nội dung do người dùng hoặc tài liệu cung cấp là dữ liệu không tin cậy (prompt injection); hành động nhạy cảm cần phân quyền, xác nhận và audit log.

## Level Guidance

### Intern

- Hiểu agent, tool và workflow; mô tả được một lời gọi tool đơn giản.

### Fresher

- Thiết kế state machine có số bước tối đa, nhánh lỗi và điều kiện dừng; xử lý retry an toàn.

### Junior

- Thiết kế workflow có phê duyệt, idempotency, durable execution, guardrails và đo chi phí/tỷ lệ thành công.

## Question Seeds

### agent_01 — Một chatbot LLM thông thường khác gì một agent có thể gọi tool?
**Levels:** intern, fresher
**Objective:** Phân biệt chatbot thuần với agent có khả năng hành động qua tool.
**Expected points:**
- Agent có thể chọn gọi tool để lấy dữ liệu hoặc thực hiện tác vụ, thay vì chỉ sinh văn bản.
- Mỗi tool có contract rõ ràng về input/output.
- Cần giới hạn quyền và kiểm tra kết quả tool.
**Follow-up probes:**
- Nếu tool báo lỗi thì agent nên làm gì?
- Khi nào chỉ cần một workflow cố định là đủ?
**Scoring caution:** Không chấp nhận quan niệm agent được tự do làm mọi việc.

### agent_02 — Function calling hoạt động thế nào: mô hình "gọi" tool ra sao và ai thực sự thực thi tool?
**Levels:** intern, fresher
**Objective:** Hiểu cơ chế tool calling và trách nhiệm của ứng dụng.
**Expected points:**
- Ứng dụng khai báo tool kèm schema tham số cho mô hình.
- Mô hình trả về lời gọi có cấu trúc (tên tool và tham số), không tự thực thi.
- Ứng dụng kiểm tra tham số, thực thi tool và gửi kết quả lại cho mô hình để tiếp tục.
**Follow-up probes:**
- Nếu mô hình sinh tham số sai schema thì xử lý thế nào?
- Vì sao không nên cho mô hình gọi trực tiếp câu lệnh SQL tùy ý?
**Scoring caution:** Không chấp nhận "mô hình tự chạy code hoặc tự gọi API".

### agent_03 — Thiết kế một agent phỏng vấn biết hỏi sâu theo câu trả lời và kết thúc đúng thời gian.
**Levels:** fresher, junior
**Objective:** Thiết kế state và giới hạn cứng cho một agent hội thoại nhiều lượt.
**Expected points:**
- State gồm kế hoạch câu hỏi, các lượt trả lời, độ phủ chủ đề và ngân sách thời gian/lượt.
- Quy tắc rõ ràng cho hỏi sâu, chuyển câu và kết thúc.
- Giới hạn cứng nằm ở backend, không phụ thuộc vào việc LLM tự tuân thủ.
**Follow-up probes:**
- Nếu LLM luôn đề xuất hỏi thêm thì sao?
- Làm sao tránh lặp câu hỏi sau khi request bị retry?
**Scoring caution:** Không coi việc nhắc "hỏi tối đa 2 lần" trong prompt là giới hạn cứng.

### agent_04 — Tool tạo ticket bị timeout, agent thử lại và tạo ra hai ticket. Bạn sửa hệ thống thế nào?
**Levels:** fresher, junior
**Objective:** Xử lý retry an toàn cho tool có tác dụng phụ.
**Expected points:**
- Dùng idempotency key cho mỗi hành động logic.
- Phân biệt lỗi có thể retry an toàn với trường hợp không rõ tác dụng phụ đã xảy ra chưa.
- Kiểm tra kết quả đã tồn tại trước khi thực hiện lại thao tác.
**Follow-up probes:**
- Bạn ghi log những ID nào để điều tra?
- Khi nào cần người dùng xác nhận trước khi thực hiện?
**Scoring caution:** Không chấp nhận retry vô hạn với tác vụ thay đổi dữ liệu.

### agent_05 — Bạn cần thêm hành động hoàn tiền vào agent chăm sóc khách hàng. Thiết kế các guardrail tối thiểu.
**Levels:** junior
**Objective:** Thiết kế an toàn cho hành động nhạy cảm do agent đề xuất.
**Expected points:**
- Phân quyền và xác nhận rõ ràng trước khi thực hiện giao dịch.
- Tool có schema chặt, giới hạn số tiền, idempotency và audit log.
- Tách đề xuất của LLM khỏi bước thực thi do backend kiểm soát.
**Follow-up probes:**
- Nếu nội dung tài liệu yêu cầu bỏ qua chính sách thì sao?
- Bạn đo tỷ lệ hoàn thành tác vụ và tỷ lệ gọi tool sai thế nào?
**Scoring caution:** Không thực thi hành động nhạy cảm chỉ dựa trên văn bản chưa xác thực.

## Scoring Rubric

- technical_accuracy: 0.35 — Kiến trúc và state đúng; hiểu đúng cơ chế tool calling và vai trò của backend.
- completeness: 0.25 — Đối chiếu expected points của từng câu.
- reasoning: 0.25 — Độ tin cậy và an toàn: retry/idempotency, giới hạn cứng, phân quyền, chống prompt injection.
- practical_examples: 0.15 — Ví dụ và cách đo lường (tỷ lệ thành công, chi phí, lỗi gọi tool).

## Positive Signals

- Đề xuất state và điều kiện dừng cụ thể.
- Tách quyết định của LLM khỏi phần thực thi do backend kiểm soát.
- Không dùng agent hoặc multi-agent khi workflow cố định đã đủ.

## Pitfalls

- Dùng multi-agent cho mọi bước dù không cần.
- Không có idempotency, audit hay điều kiện dừng.
- Tin tưởng nội dung từ tài liệu người dùng như chỉ dẫn hệ thống.

## References

- LangGraph overview — https://docs.langchain.com/oss/python/langgraph/overview
- LangGraph persistence — https://docs.langchain.com/oss/python/langgraph/persistence
- OWASP Top 10 for LLM Applications — https://genai.owasp.org/llm-top-10/

## Changelog

- 1.0.1 (2026-11-03): Thêm keyword "llm", "agent", "ai agent" để nhận diện yêu cầu JD (không đổi nội dung chấm).
- 1.0.0 (2026-11-03): Chuyển đổi từ IntervAI Skill Library v1.0, thêm câu function calling; chờ review.
