---
id: data_processing
kind: competency_skill
version: 1.0.0
assessment: question
levels: [intern, fresher, junior]
keywords: [spark, pyspark, pandas, polars, dask, parquet, hadoop, databricks, partition, shuffle, data skew, big data, duckdb]
status: draft
---

# Scalable Data Processing

## Learning Objectives

- Chọn pandas, SQL engine hay Spark theo khối lượng dữ liệu và nhu cầu.
- Hiểu partition, shuffle, skew, bộ nhớ và bố cục file.
- Tối ưu hiệu năng mà vẫn kiểm chứng được tính đúng của dữ liệu.

## Core Knowledge

- pandas phù hợp dữ liệu vừa RAM; xử lý theo chunk, SQL engine nhúng (ví dụ DuckDB) hoặc Spark khi dữ liệu lớn hơn. Spark phân tán được nhưng có overhead.
- Định dạng cột (Parquet) chỉ đọc các cột cần, nén tốt và lưu thống kê giúp bỏ qua dữ liệu không liên quan; CSV phải đọc toàn bộ và không có kiểu dữ liệu.
- Partition ảnh hưởng mức song song và bố cục file; quá nhiều file nhỏ gây overhead lớn.
- JOIN và groupBy có thể gây shuffle lớn; khóa bị lệch (skew) tạo task chạy rất lâu. Broadcast join phù hợp khi một bảng đủ nhỏ để chép tới mọi executor.
- Partition pruning và predicate pushdown chỉ hiệu quả khi truy vấn lọc đúng trên cột partition/cột có thống kê.
- Tính đúng cần schema, kiểu dữ liệu, ngữ nghĩa NULL và đối soát kết quả.

## Level Guidance

### Intern

- Phân biệt pandas/SQL/Spark, hiểu xử lý theo chunk, bộ nhớ và lợi ích của Parquet.

### Fresher

- Thiết kế batch Spark với chiến lược partition và join phù hợp; nhận diện skew.

### Junior

- Phân tích shuffle/skew qua physical plan và metric, tối ưu chi phí tính toán và bố cục dữ liệu.

## Question Seeds

### dp_01 — Một file CSV 12 GB không vừa RAM của máy 8 GB. Bạn xử lý thế nào?
**Levels:** intern, fresher
**Objective:** Chọn cách xử lý phù hợp khi dữ liệu lớn hơn bộ nhớ.
**Expected points:**
- Không nạp toàn bộ bằng pandas theo mặc định.
- Xử lý theo chunk, dùng SQL engine hoặc Spark tùy bài toán.
- Chọn kiểu dữ liệu/chỉ đọc cột cần thiết và lưu kết quả trung gian hợp lý (ví dụ Parquet).
**Follow-up probes:**
- Nếu chỉ cần tổng doanh thu theo ngày thì cách nào đơn giản nhất?
- Chuyển sang Parquet giúp gì?
**Scoring caution:** Không cần Spark cho mọi bài toán dữ liệu lớn.

### dp_02 — Vì sao định dạng cột như Parquet thường nhanh hơn CSV cho truy vấn phân tích?
**Levels:** intern, fresher
**Objective:** Hiểu lợi ích của định dạng lưu trữ dạng cột.
**Expected points:**
- Chỉ đọc các cột cần thiết thay vì toàn bộ dòng.
- Nén hiệu quả hơn và lưu kiểu dữ liệu.
- Có thống kê (min/max) giúp bỏ qua khối dữ liệu không liên quan khi lọc.
**Follow-up probes:**
- Khi nào CSV vẫn hợp lý hơn?
- Partition theo ngày giúp gì cho truy vấn một tuần?
**Scoring caution:** Không chấp nhận "Parquet nhanh vì là file nhị phân" mà không giải thích cơ chế.

### dp_03 — Spark job join một bảng sự kiện rất lớn với bảng danh mục sản phẩm nhỏ. Bạn chọn chiến lược nào?
**Levels:** fresher, junior
**Objective:** Chọn chiến lược join dựa trên kích thước dữ liệu và kiểm chứng bằng plan.
**Expected points:**
- Đánh giá kích thước bảng danh mục và bộ nhớ executor.
- Dùng broadcast join khi bảng nhỏ phù hợp để tránh shuffle bảng lớn.
- Kiểm tra physical plan và metric của job.
**Follow-up probes:**
- Nếu bảng danh mục tăng kích thước đột ngột thì sao?
- Bạn tránh nghẽn ở driver khi broadcast thế nào?
**Scoring caution:** Không khuyên broadcast khi không biết kích thước bảng.

### dp_04 — Spark groupBy theo customer_id có vài khách hàng rất lớn làm một số task chạy rất lâu. Bạn xử lý thế nào?
**Levels:** fresher, junior
**Objective:** Nhận diện và xử lý data skew mà vẫn giữ kết quả đúng.
**Expected points:**
- Nhận diện data skew qua metric của task (thời gian, kích thước dữ liệu không đều).
- Cân nhắc salting hoặc tổng hợp hai giai đoạn.
- Đo lại shuffle, partition và kiểm tra tính đúng của kết quả.
**Follow-up probes:**
- Nếu cần kết quả tổng hợp chính xác tuyệt đối thì sao?
- Bạn kiểm thử với các khóa "nóng" thế nào?
**Scoring caution:** Không chấp nhận tăng số partition một cách mù quáng.

### dp_05 — Job đọc 6 tháng dữ liệu Parquet trong khi truy vấn chỉ cần một tuần, nhưng vẫn chậm. Bạn kiểm tra gì?
**Levels:** junior
**Objective:** Chẩn đoán partition pruning, bố cục file và lượng dữ liệu bị quét.
**Expected points:**
- Xác nhận điều kiện lọc có áp lên cột partition và predicate pushdown có hoạt động.
- Rà schema và bố cục file, vấn đề nhiều file nhỏ.
- Đo lượng byte bị quét, mức pruning; cân nhắc compaction hoặc ghi lại dữ liệu.
**Follow-up probes:**
- Nếu partition theo ngày tạo ra quá nhiều file nhỏ thì sao?
- Khi nào nên dùng clustering hoặc Z-order?
**Scoring caution:** Không khẳng định Parquet luôn được pruning nếu truy vấn không lọc đúng.

## Scoring Rubric

- technical_accuracy: 0.40 — Hiểu đúng partition, shuffle, skew, định dạng lưu trữ.
- completeness: 0.25 — Đối chiếu expected points của từng câu.
- reasoning: 0.25 — Chọn công cụ có lý do; đo bằng plan/metric và kiểm chứng tính đúng.
- practical_examples: 0.10 — Ví dụ thực tế về hiệu năng và chi phí.

## Positive Signals

- Đọc physical plan và metric thay vì tối ưu cảm tính.
- Nhắc tới bộ nhớ, skew và kiểm tra tính đúng của dữ liệu.
- Chọn công cụ đơn giản nhất đủ cho khối lượng dữ liệu.

## Pitfalls

- Chỉ biết cú pháp Spark, không hiểu shuffle.
- Tăng tài nguyên cluster thay vì xem skew hoặc bố cục file.
- Dùng Spark cho dữ liệu nhỏ.

## References

- Apache Spark, SQL Performance Tuning — https://spark.apache.org/docs/latest/sql-performance-tuning.html
- Apache Parquet documentation — https://parquet.apache.org/docs/
- pandas, Scaling to large datasets — https://pandas.pydata.org/docs/user_guide/scale.html

## Changelog

- 1.0.0 (2026-11-03): Chuyển đổi từ IntervAI Skill Library v1.0, thêm câu Parquet; chờ review.
