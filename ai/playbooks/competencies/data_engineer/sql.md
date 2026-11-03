---
id: sql
kind: competency_skill
version: 1.0.0
assessment: question
levels: [intern, fresher, junior]
keywords: [sql, join, group by, window function, cte, query optimization, bigquery, snowflake, postgresql, mysql, analytics]
status: draft
---

# SQL Querying & Analytics

## Learning Objectives

- Viết truy vấn đúng với JOIN, GROUP BY, window function.
- Nhận diện các bẫy về tính đúng: NULL, trùng lặp do JOIN, grain của bảng.
- Phân tích và cải thiện hiệu năng truy vấn.

## Core Knowledge

- INNER JOIN chỉ giữ các cặp khớp; LEFT JOIN giữ mọi dòng bên trái kể cả khi không khớp.
- WHERE lọc từng dòng trước khi gom nhóm; HAVING lọc sau khi GROUP BY dựa trên giá trị tổng hợp.
- Window function tính trên một partition mà vẫn giữ nguyên số dòng; ROW_NUMBER, RANK, LAG, LEAD, SUM() OVER thường gặp. Khung ROWS tính theo số dòng, RANGE tính theo giá trị.
- JOIN hai bảng quan hệ 1-n với cùng một bảng cha có thể nhân bản dòng (fan-out), làm tổng bị phóng đại; cần xác định grain và tổng hợp trước khi JOIN.
- NULL dùng logic ba giá trị; COUNT(*) đếm mọi dòng, COUNT(cột) bỏ qua NULL.
- Hiệu năng phụ thuộc lọc sớm, index/partition, tổng hợp trước và query plan.

## Level Guidance

### Intern

- JOIN, GROUP BY và điều kiện lọc đúng; phân biệt WHERE và HAVING.

### Fresher

- Truy vấn báo cáo với window function, xử lý trùng lặp và trường hợp hòa (tie).

### Junior

- Tối ưu truy vấn với index/partition, đọc query plan, xử lý edge case như múi giờ và dữ liệu đến muộn.

## Question Seeds

### sql_01 — Lấy tổng số đơn của từng khách hàng, bao gồm cả khách chưa từng đặt đơn.
**Levels:** intern, fresher
**Objective:** Dùng đúng LEFT JOIN và hàm đếm với NULL.
**Expected points:**
- LEFT JOIN từ customers sang orders để giữ khách chưa có đơn.
- GROUP BY theo mã khách hàng.
- Dùng COUNT(order_id) để khách chưa có đơn ra 0.
**Follow-up probes:**
- Nếu dùng COUNT(*) thì kết quả sai ở đâu?
- Bạn xử lý khách hàng trùng tên thế nào?
**Scoring caution:** Không chấp nhận INNER JOIN khi yêu cầu có cả khách chưa mua.

### sql_02 — Phân biệt WHERE và HAVING, và cho một ví dụ bắt buộc phải dùng HAVING.
**Levels:** intern, fresher
**Objective:** Hiểu thứ tự lọc trước và sau khi tổng hợp.
**Expected points:**
- WHERE lọc từng dòng trước khi gom nhóm.
- HAVING lọc sau GROUP BY dựa trên giá trị tổng hợp.
- Ví dụ: tìm khách có tổng giá trị đơn trên một ngưỡng (HAVING SUM(amount) > ...).
**Follow-up probes:**
- Điều kiện lọc theo thời gian nên đặt ở WHERE hay HAVING, vì sao?
- Có thể dùng alias của cột tổng hợp trong WHERE không?
**Scoring caution:** Không chấp nhận đặt điều kiện trên từng dòng vào HAVING mà không giải thích hệ quả.

### sql_03 — Từ bảng purchases, lấy đơn mua đầu tiên và gần nhất của mỗi người dùng.
**Levels:** fresher, junior
**Objective:** Dùng window function đúng, xử lý trường hợp hòa.
**Expected points:**
- Phân nhóm theo người dùng và sắp xếp theo thời gian.
- Dùng ROW_NUMBER hoặc window phù hợp (FIRST_VALUE, MIN/MAX theo thời gian).
- Xử lý trùng thời gian bằng tiêu chí phụ (tie-breaker).
**Follow-up probes:**
- Nếu có đơn bị hoàn trả, bạn đổi logic thế nào?
- Truy vấn còn hiệu quả trên hàng triệu dòng không?
**Scoring caution:** Không coi MIN(amount) là đơn đầu tiên.

### sql_04 — Doanh thu trong báo cáo tăng gấp đôi sau khi JOIN orders với order_items và payments. Vì sao?
**Levels:** fresher, junior
**Objective:** Nhận diện fan-out do JOIN và xác định đúng grain.
**Expected points:**
- Nhận ra JOIN nhân bản dòng khi cả hai bảng đều quan hệ 1-n với orders.
- Tổng hợp từng bảng theo order trước khi JOIN, hoặc chọn grain phù hợp.
- Kiểm tra số dòng và tính duy nhất của khóa sau mỗi bước JOIN.
**Follow-up probes:**
- Dùng COUNT DISTINCT có thực sự sửa được tổng tiền không?
- Grain của một bảng fact là gì?
**Scoring caution:** Không chấp nhận dùng DISTINCT tùy tiện mà không xét grain.

### sql_05 — Truy vấn tính doanh thu lũy kế 30 ngày (rolling revenue) chạy chậm trên bảng sự kiện lớn. Bạn cải thiện thế nào?
**Levels:** junior
**Objective:** Tối ưu truy vấn phân tích mà vẫn giữ tính đúng.
**Expected points:**
- Làm rõ khung cửa sổ (theo ngày lịch hay theo số dòng), lọc thời gian sớm, dùng index/partition.
- Tổng hợp trước theo ngày rồi mới tính cửa sổ; kiểm tra query plan.
- Giữ tính đúng với múi giờ và dữ liệu đến muộn.
**Follow-up probes:**
- Rolling theo 30 ngày lịch khác gì 30 dòng gần nhất?
- Bạn so sánh query plan và latency trước/sau thế nào?
**Scoring caution:** Không nhầm khung ROWS với RANGE.

## Scoring Rubric

- technical_accuracy: 0.45 — Logic SQL đúng: loại JOIN, thứ tự lọc, window function.
- completeness: 0.25 — Đối chiếu expected points, gồm edge case NULL, trùng lặp, tie.
- reasoning: 0.20 — Giải thích grain và phân tích hiệu năng có căn cứ.
- practical_examples: 0.10 — Giải thích rõ, có cách kiểm chứng kết quả với dữ liệu nhỏ.

## Positive Signals

- Xác định grain trước khi JOIN hoặc tổng hợp.
- Kiểm thử truy vấn với tập dữ liệu nhỏ đã biết đáp án.
- Nhắc tới NULL và trường hợp hòa mà không cần gợi ý.

## Pitfalls

- Dùng COUNT(*) sau LEFT JOIN mà không hiểu hệ quả.
- Dùng DISTINCT để che lỗi nhân bản doanh thu.
- Lọc trên cột đã biến đổi làm mất khả năng dùng index.

## References

- PostgreSQL Tutorial — https://www.postgresql.org/docs/current/tutorial.html
- PostgreSQL, Window Functions — https://www.postgresql.org/docs/current/tutorial-window.html
- PostgreSQL, Using EXPLAIN — https://www.postgresql.org/docs/current/using-explain.html

## Changelog

- 1.0.0 (2026-11-03): Chuyển đổi từ IntervAI Skill Library v1.0, thêm câu WHERE/HAVING; chờ review.
