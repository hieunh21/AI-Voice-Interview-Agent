---
id: problem_solving
kind: competency_skill
version: 1.0.0
assessment: cross_cutting
levels: [intern, fresher, junior]
keywords: []
status: draft
---

# Engineering Problem Solving

## Learning Objectives

- Tiếp cận vấn đề có cấu trúc: làm rõ yêu cầu → tái hiện → khoanh vùng → đo → sửa → kiểm chứng.
- Đặt giả thuyết có thể kiểm chứng thay vì đoán mò.
- Ứng xử trung thực khi gặp câu hỏi vượt quá hiểu biết.

## Core Knowledge

- Phân biệt triệu chứng và nguyên nhân gốc; tạo ví dụ tái hiện tối giản.
- Đặt tiêu chí thành công trước khi thay đổi; thay đổi từng yếu tố một và so với baseline.
- Ưu tiên giải pháp đơn giản, có khả năng quay lui và có test chống tái phát; với sự cố đang diễn ra, chú ý phạm vi ảnh hưởng và tính toàn vẹn dữ liệu.
- Khi chưa biết: nói rõ phần chưa chắc, suy luận từ nguyên lý đã biết và đề xuất cách kiểm chứng.

## Level Guidance

### Intern

- Biết hỏi lại yêu cầu và chia bài toán thành các bước nhỏ.

### Fresher

- Lập kế hoạch debug và chứng minh bản sửa không làm hỏng chức năng khác.

### Junior

- Ưu tiên hành động dưới áp lực thời gian; cân bằng giữa giải pháp tạm và sửa tận gốc.

## Scoring Rubric

- decomposition: 0.40 — Đặt đúng vấn đề, làm rõ giả định và chia thành các bước hợp lý.
- hypothesis_testing: 0.30 — Giả thuyết có thể kiểm chứng, đo trước khi kết luận, xác nhận bản sửa.
- handling_uncertainty: 0.30 — Thừa nhận giới hạn, không bịa; phân biệt điều chắc chắn với phỏng đoán.

## Positive Signals

- Đặt câu hỏi làm rõ thay vì nhảy ngay vào công nghệ.
- Phân biệt sửa tạm, nguyên nhân gốc và biện pháp phòng ngừa.
- Thay đổi từng yếu tố một và đo lại.

## Pitfalls

- Thay đổi nhiều thứ cùng lúc rồi tuyên bố đã tối ưu thành công.
- Chỉ "restart service" mà không tìm nguyên nhân.
- Khẳng định chắc chắn điều chưa kiểm chứng.

## References

- Google SRE Workbook — https://sre.google/workbook/table-of-contents/
- Python Logging HOWTO — https://docs.python.org/3/howto/logging.html

## Changelog

- 1.0.0 (2026-11-03): Chuyển đổi từ IntervAI Skill Library v1.0 thành skill chấm trên toàn buổi; các câu tình huống được chuyển sang programming_fundamentals, model_evaluation, etl_pipeline và system_design; chờ review.
