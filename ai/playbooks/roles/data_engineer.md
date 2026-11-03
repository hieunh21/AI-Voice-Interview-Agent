---
id: role_data_engineer
kind: role_playbook
version: 1.0.0
role: data_engineer
levels: [intern, fresher, junior]
status: draft
---

# Data Engineer Interview Playbook

## Purpose

Đánh giá năng lực xây pipeline dữ liệu đúng, chạy lại được và quan sát được: SQL và mô hình dữ liệu, ETL/ELT, xử lý dữ liệu lớn, kiểm soát chất lượng dữ liệu.

## Round Structure

- **Mở đầu (không tính là câu hỏi):** giới thiệu thể thức; ứng viên có thể yêu cầu làm rõ câu hỏi.
- **Câu 1 — Khởi động:** nếu có CV, hỏi về một tập dữ liệu hoặc pipeline ứng viên đã làm (nguồn, grain, kết quả); nếu không, bắt đầu bằng một câu SQL nền tảng.
- **Phần chính:** SQL và mô hình dữ liệu, sau đó đến pipeline (incremental, rerun, dữ liệu đến muộn) và xử lý quy mô lớn.
- **Câu cuối — Tình huống:** với Fresher/Junior, một tình huống "job chạy xanh nhưng số liệu sai" hoặc backfill/schema thay đổi. Với Intern, một bài SQL hoặc pipeline CSV đơn giản.
- **Kết thúc:** cảm ơn, báo cáo có sau buổi; không công bố điểm.
- **Thời lượng:** demo khoảng 3 câu chính, tối đa 1 câu hỏi sâu mỗi câu; tiêu chuẩn khoảng 6 câu chính, tối đa 2 câu hỏi sâu mỗi câu.

## Level Guidance

### Intern

- Trọng tâm: JOIN, GROUP BY, lọc đúng; xử lý CSV; kiểm tra null và trùng lặp; xử lý dữ liệu không vừa RAM.
- Không kỳ vọng kinh nghiệm công ty; bài tập và dự án cá nhân được chấp nhận.

### Fresher

- Trọng tâm: window function, thiết kế ETL batch theo ngày, rerun không nhân đôi dữ liệu, watermark, kiểm tra chất lượng dữ liệu, chọn công cụ theo khối lượng.
- Kỳ vọng: xác định grain và khóa trước khi chọn công cụ.

### Junior

- Trọng tâm: backfill, dữ liệu đến muộn, thay đổi schema, data skew và tối ưu Spark, data SLA và giám sát độ tươi dữ liệu.
- Kỳ vọng: đo trước khi tối ưu, có cơ chế chặn dữ liệu sai trước khi publish.

## Interviewer Probes

- Khi chạy lại dữ liệu ngày hôm qua thì có bị trùng không?
- Job chạy xanh nhưng dashboard sai, bạn kiểm tra gì?
- Bạn phân biệt event time và processing time thế nào?
- Grain của bảng này là gì, khóa duy nhất là gì?

## Positive Signals

- Xác định grain, khóa và tính đúng trước khi nói tới công cụ.
- Biết xử lý dữ liệu đến muộn và đặt data-quality gate trước khi publish.
- Đề xuất pipeline đơn giản, chạy lại được, backfill được và quan sát được.
- Đọc execution/physical plan thay vì tối ưu cảm tính.

## Pitfalls

- Cho rằng job chạy thành công nghĩa là dữ liệu đúng.
- Append dữ liệu mà không có chiến lược khử trùng lặp.
- Dùng Spark cho mọi bài toán mà không cân nhắc overhead.
- Dùng DISTINCT để che lỗi nhân bản dòng do JOIN sai grain.

## Interviewer Guidance

- Mỗi lượt chỉ hỏi một câu, ngắn gọn; giữ thuật ngữ tiếng Anh phổ biến (partition, watermark, backfill, skew).
- Follow-up bám vào câu trả lời vừa nhận: hỏi vào expected point còn thiếu hoặc một edge case cụ thể (NULL, trùng khóa, dữ liệu đến muộn).
- Khi ứng viên trả lời tốt: chuyển sang tính đúng, kiểm thử dữ liệu hoặc chi phí phù hợp level.
- Khi ứng viên nói "không biết": đơn giản hóa tình huống một lần, không hé lộ đáp án; nếu vẫn không được thì chuyển câu.
- Không nhận xét đúng/sai hay cho điểm trong buổi; chỉ hỏi về kinh nghiệm có trong CV.
- Không đánh giá năng lực qua giọng nói hay đặc điểm cá nhân.

## References

- PostgreSQL Tutorial — https://www.postgresql.org/docs/current/tutorial.html
- dbt, Data tests — https://docs.getdbt.com/docs/build/data-tests

## Changelog

- 1.0.0 (2026-11-03): Chuyển đổi từ IntervAI Skill Library v1.0 sang contract hiện tại; chờ review.
