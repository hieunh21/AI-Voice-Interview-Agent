---
id: databases
kind: competency_skill
version: 1.0.0
assessment: question
levels: [intern, fresher, junior]
keywords: [postgresql, postgres, mysql, sql server, database, index, transaction, orm, sqlalchemy, prisma, hibernate, migration, alembic, schema design, acid]
status: draft
---

# Relational Database Design

## Learning Objectives

- Thiết kế schema có khóa, ràng buộc và quan hệ đúng.
- Chọn index dựa trên truy vấn thực tế và đọc query plan.
- Đảm bảo tính đúng khi nhiều transaction chạy đồng thời; thực hiện migration an toàn.

## Core Knowledge

- Primary key định danh dòng; foreign key giữ ràng buộc tham chiếu, cần chọn hành vi ON DELETE phù hợp.
- Chuẩn hóa giảm trùng lặp; phi chuẩn hóa có chủ đích khi cần tối ưu đọc, kèm chi phí đồng bộ dữ liệu.
- Index tăng tốc lọc/join/sắp xếp nhưng tốn chi phí ghi và bộ nhớ; với index nhiều cột, thứ tự cột quan trọng. Dùng EXPLAIN ANALYZE để kiểm chứng thay vì đoán.
- ACID và mức isolation quyết định các bất thường khi chạy đồng thời (lost update, dirty/non-repeatable read, phantom). Có thể dùng cập nhật có điều kiện, khóa hàng (SELECT ... FOR UPDATE) hoặc ràng buộc unique để bảo vệ tính đúng.
- Migration trên bảng lớn cần tương thích ngược theo từng bước (expand → migrate → contract), backfill theo lô và có kế hoạch rollback.

## Level Guidance

### Intern

- Thiết kế bảng quan hệ 1-n, khóa chính/khóa ngoại và JOIN cơ bản; hiểu index ở mức khái niệm.

### Fresher

- Chọn index phù hợp, dùng transaction và ràng buộc để bảo vệ tính toàn vẹn.

### Junior

- Phân tích execution plan, bất thường khi chạy đồng thời, migration không downtime.

## Question Seeds

### db_01 — Thiết kế các bảng users, orders và order_items cho một ứng dụng bán hàng.
**Levels:** intern, fresher
**Objective:** Thiết kế schema quan hệ với khóa và ràng buộc đúng.
**Expected points:**
- Mỗi bảng có primary key; foreign key thể hiện đúng quan hệ.
- Mô tả quan hệ 1-n giữa users–orders và orders–order_items.
- Không lưu nhiều mặt hàng trong một cột không có cấu trúc; lưu giá tại thời điểm mua trong order_items.
**Follow-up probes:**
- Đơn hàng cần lưu giá tại thời điểm mua thế nào, vì sao?
- Bạn lấy tất cả đơn hàng của một người dùng bằng JOIN ra sao?
**Scoring caution:** Không khẳng định có một schema tối ưu cho mọi nghiệp vụ.

### db_02 — Index là gì, vì sao giúp truy vấn nhanh hơn, và nó có nhược điểm gì?
**Levels:** intern, fresher
**Objective:** Hiểu cơ chế và chi phí của index.
**Expected points:**
- Index là cấu trúc dữ liệu (thường là B-tree) giúp tìm dòng theo giá trị mà không quét toàn bảng.
- Hữu ích cho lọc, join và sắp xếp trên cột được đánh index.
- Nhược điểm: tốn bộ nhớ và làm chậm thao tác ghi; index không phù hợp có thể không được dùng.
**Follow-up probes:**
- Vì sao không nên đánh index cho mọi cột?
- Bạn kiểm tra một truy vấn có dùng index hay không bằng cách nào?
**Scoring caution:** Không chấp nhận "index luôn làm truy vấn nhanh hơn".

### db_03 — Một truy vấn lọc orders theo user_id, status và created_at ngày càng chậm. Bạn làm gì?
**Levels:** fresher, junior
**Objective:** Tối ưu truy vấn dựa trên đo đạc và chọn index phù hợp.
**Expected points:**
- Đo bằng EXPLAIN ANALYZE trước khi sửa.
- Xem độ chọn lọc của điều kiện và đề xuất index (có thể là index nhiều cột) phù hợp.
- Cân nhắc sắp xếp/phân trang và chi phí ghi của index mới.
**Follow-up probes:**
- Khi nào thêm index mới mà vẫn không giúp được?
- Với index nhiều cột, vì sao thứ tự cột quan trọng?
**Scoring caution:** Không thêm index lên mọi cột.

### db_04 — Hai request cùng lúc mua món hàng chỉ còn 1 chiếc trong kho. Bạn đảm bảo không bán quá số lượng thế nào?
**Levels:** fresher, junior
**Objective:** Bảo vệ tính đúng khi nhiều transaction chạy đồng thời.
**Expected points:**
- Dùng transaction với cập nhật có điều kiện (ví dụ chỉ trừ khi tồn kho còn đủ) hoặc khóa hàng hợp lý.
- Kiểm tra số dòng bị ảnh hưởng và trả lỗi hết hàng cho request thua.
- Tái hiện tình huống đồng thời trong kiểm thử.
**Follow-up probes:**
- Nếu transaction bị timeout thì sao?
- Optimistic locking và pessimistic locking khác nhau thế nào?
**Scoring caution:** Không tin vào việc kiểm tra tồn kho chỉ ở frontend hoặc kiểm tra rồi mới ghi mà không có khóa.

### db_05 — Bạn cần đổi một cột thành bắt buộc trên bảng hàng triệu dòng mà không dừng dịch vụ. Lên kế hoạch thế nào?
**Levels:** junior
**Objective:** Thực hiện migration không downtime, tương thích ngược.
**Expected points:**
- Chia bước expand → migrate → contract.
- Backfill theo lô và theo dõi tiến độ.
- Code đọc/ghi tương thích với cả hai trạng thái; có kiểm thử và kế hoạch rollback; chỉ thêm NOT NULL sau khi dữ liệu đầy đủ.
**Follow-up probes:**
- Nếu backfill thất bại giữa chừng thì sao?
- Khi nào mới thêm ràng buộc NOT NULL?
**Scoring caution:** Không chấp nhận ALTER làm hỏng client cũ khi chưa chuẩn bị.

## Scoring Rubric

- technical_accuracy: 0.40 — Schema, ràng buộc, index và transaction đúng.
- completeness: 0.25 — Đối chiếu expected points của từng câu.
- reasoning: 0.20 — Lựa chọn dựa trên workload và tính đúng khi đồng thời; đo bằng query plan.
- practical_examples: 0.15 — Ví dụ thực tế về migration, tối ưu truy vấn hoặc xử lý concurrency.

## Positive Signals

- Lựa chọn dựa trên workload truy vấn và tính đúng của dữ liệu.
- Biết trade-off giữa index và chi phí ghi.
- Đo bằng query plan trước khi tối ưu.

## Pitfalls

- Không dùng transaction cho thao tác nhiều bước cần tính nguyên tử.
- Sửa schema không có migration và phương án quay lui.
- Kiểm tra rồi mới ghi mà không có khóa hay ràng buộc.

## References

- PostgreSQL Tutorial — https://www.postgresql.org/docs/current/tutorial.html
- PostgreSQL, Indexes — https://www.postgresql.org/docs/current/indexes.html
- PostgreSQL, Transaction Isolation — https://www.postgresql.org/docs/current/transaction-iso.html

## Changelog

- 1.0.0 (2026-11-03): Chuyển đổi từ IntervAI Skill Library v1.0, thêm câu index cơ bản; chờ review.
