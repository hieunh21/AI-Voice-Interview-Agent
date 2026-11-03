---
id: role_backend_developer
kind: role_playbook
version: 1.0.0
role: backend_developer
levels: [intern, fresher, junior]
status: draft
---

# Backend Developer Interview Playbook

## Purpose

Đánh giá tư duy xây dựng API và tầng dữ liệu đúng, an toàn và vận hành được: thiết kế API, mô hình dữ liệu, transaction và concurrency, xử lý lỗi, hiệu năng và khả năng quan sát hệ thống.

## Round Structure

- **Mở đầu (không tính là câu hỏi):** giới thiệu thể thức; ứng viên có thể yêu cầu làm rõ câu hỏi.
- **Câu 1 — Khởi động:** nếu có CV, hỏi về một API hoặc tính năng ứng viên đã viết; nếu không, bắt đầu bằng câu nền tảng về HTTP/API hoặc lập trình.
- **Phần chính:** thiết kế API và mô hình dữ liệu, sau đó đến tính đúng khi chạy đồng thời (transaction, idempotency) và hiệu năng truy vấn.
- **Câu cuối — Tình huống:** với Fresher/Junior, một tình huống debug hoặc độ tin cậy (retry, timeout, P95 tăng, migration). Với Intern, một bài thiết kế bảng hoặc API đơn giản.
- **Kết thúc:** cảm ơn, báo cáo có sau buổi; không công bố điểm.
- **Thời lượng:** demo khoảng 3 câu chính, tối đa 1 câu hỏi sâu mỗi câu; tiêu chuẩn khoảng 6 câu chính, tối đa 2 câu hỏi sâu mỗi câu.

## Level Guidance

### Intern

- Trọng tâm: HTTP method và status code, CRUD, thiết kế bảng quan hệ 1-n, JOIN cơ bản, cấu trúc dữ liệu và debug có trình tự.
- Không kỳ vọng kinh nghiệm công ty; bài tập và dự án cá nhân được chấp nhận.

### Fresher

- Trọng tâm: validation, xác thực và phân quyền, phân trang, index, transaction, kiểm thử API, xử lý tác vụ chạy nền.
- Kỳ vọng: giải thích được lựa chọn, có nghĩ tới trường hợp lỗi chứ không chỉ happy path.

### Junior

- Trọng tâm: tương thích ngược, idempotency, concurrency, migration không downtime, async job và worker restart, SLO, giám sát.
- Kỳ vọng: đo trước khi tối ưu, nêu failure mode và cách phục hồi, cân nhắc trade-off nhất quán – hiệu năng.

## Interviewer Probes

- Nếu request bị retry hoặc hai request chạy đồng thời thì chuyện gì xảy ra?
- Bạn viết integration test để xác nhận điều gì?
- Khi dữ liệu tăng gấp 100 lần, bạn đo điểm nghẽn nào trước?
- Ai được phép gọi API này, và server kiểm tra quyền ở đâu?

## Positive Signals

- Phân biệt xác thực (authentication) với phân quyền (authorization); kiểm tra quyền ở server.
- Có kế hoạch kiểm thử trường hợp lỗi, retry và biên phân trang, không chỉ happy path.
- Đo truy vấn hoặc endpoint trước khi thêm cache hay scale.
- Bắt đầu từ thiết kế đơn giản và nói rõ khi nào cần phức tạp hơn.

## Pitfalls

- Chỉ kiểm tra quyền ở frontend.
- Đề xuất microservices khi chưa có nhu cầu.
- Không quan tâm idempotency khi hệ thống có retry.
- Dùng HTTP 200 cho mọi trạng thái mà không có contract rõ ràng.
- Thêm index lên mọi cột hoặc tối ưu cảm tính khi chưa đo.

## Interviewer Guidance

- Mỗi lượt chỉ hỏi một câu, ngắn gọn; dùng tiếng Việt và giữ thuật ngữ tiếng Anh phổ biến (endpoint, transaction, index, idempotency).
- Follow-up bám vào câu trả lời vừa nhận: hỏi vào expected point còn thiếu hoặc một tình huống lỗi cụ thể (retry, đồng thời, timeout).
- Khi ứng viên trả lời tốt: chuyển sang kiểm thử, failure mode hoặc trade-off phù hợp level.
- Khi ứng viên nói "không biết": đơn giản hóa tình huống một lần, không hé lộ đáp án; nếu vẫn không được thì chuyển câu.
- Không nhận xét đúng/sai hay cho điểm trong buổi; chỉ hỏi về kinh nghiệm có trong CV.
- Không đánh giá năng lực qua giọng nói hay đặc điểm cá nhân.

## References

- FastAPI Tutorial — https://fastapi.tiangolo.com/tutorial/
- RFC 9110, HTTP Semantics — https://www.rfc-editor.org/rfc/rfc9110.html

## Changelog

- 1.0.0 (2026-11-03): Chuyển đổi từ IntervAI Skill Library v1.0 sang contract hiện tại; chờ review.
