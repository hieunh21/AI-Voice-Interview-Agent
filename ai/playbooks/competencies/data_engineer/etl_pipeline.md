---
id: etl_pipeline
kind: competency_skill
version: 1.0.0
assessment: question
levels: [intern, fresher, junior]
keywords: [etl, elt, data pipeline, airflow, dagster, prefect, dbt, cdc, incremental load, backfill, data quality, data warehouse, orchestration]
status: draft
---

# ETL/ELT Pipelines & Reliability

## Learning Objectives

- Thiết kế pipeline ingest → transform → load có grain và khóa rõ ràng.
- Đảm bảo chạy lại (rerun), backfill và nạp tăng dần mà không trùng hoặc mất dữ liệu.
- Kiểm soát chất lượng dữ liệu và vận hành pipeline đáng tin cậy.

## Core Knowledge

- ETL biến đổi trước khi nạp; ELT nạp dữ liệu thô rồi biến đổi trong kho dữ liệu. Lựa chọn tùy nền tảng, chi phí và yêu cầu bảo mật.
- Pipeline idempotent: chạy lại cùng đầu vào không nhân đôi dữ liệu — dùng khóa nghiệp vụ duy nhất với MERGE/UPSERT hoặc ghi đè theo partition.
- Nạp tăng dần dựa trên watermark, CDC hoặc event time; dữ liệu đến muộn cần chính sách lookback và xử lý lại partition bị ảnh hưởng.
- Kiểm thử dữ liệu: schema, NULL, tính duy nhất, toàn vẹn tham chiếu, độ tươi, số dòng và đối soát tổng.
- Orchestration gồm phụ thuộc giữa tác vụ, retry, cảnh báo, backfill và lineage. Job chạy xong không đồng nghĩa dữ liệu đúng.
- Giữ dữ liệu thô để có thể xử lý lại; cách ly (quarantine) bản ghi lỗi thay vì âm thầm loại bỏ.

## Level Guidance

### Intern

- Hiểu các bước ETL, vai trò của tầng staging và kiểm tra dữ liệu cơ bản.

### Fresher

- Thiết kế nạp tăng dần hằng ngày, rerun an toàn và kiểm tra chất lượng.

### Junior

- Xử lý dữ liệu đến muộn, backfill lớn, thay đổi schema và SLO về độ tươi dữ liệu.

## Question Seeds

### etl_01 — Giải thích các bước của pipeline lấy file CSV bán hàng để tạo bảng doanh thu theo ngày.
**Levels:** intern, fresher
**Objective:** Mô tả luồng ETL cơ bản với kiểm tra dữ liệu.
**Expected points:**
- Nạp file thô và kiểm tra schema.
- Làm sạch, chuẩn hóa, biến đổi và tổng hợp theo ngày.
- Nạp vào bảng đích kèm kiểm tra số dòng hoặc đối soát tổng.
**Follow-up probes:**
- Nếu file có dòng thiếu giá bán thì xử lý thế nào?
- Vì sao nên giữ lại dữ liệu thô?
**Scoring caution:** Không chấp nhận mặc định loại bỏ mọi bản ghi lỗi mà không ghi nhận.

### etl_02 — ETL và ELT khác nhau thế nào? Khi nào chọn cách nào?
**Levels:** intern, fresher
**Objective:** Hiểu hai mô hình xử lý và tiêu chí lựa chọn.
**Expected points:**
- ETL biến đổi trước khi nạp vào kho; ELT nạp dữ liệu thô trước rồi biến đổi trong kho.
- ELT tận dụng sức mạnh tính toán của data warehouse và giữ được dữ liệu thô để xử lý lại.
- ETL phù hợp khi cần làm sạch/ẩn dữ liệu nhạy cảm trước khi nạp hoặc kho đích hạn chế.
**Follow-up probes:**
- Công cụ như dbt thường thuộc bước nào?
- Lưu dữ liệu thô có rủi ro gì về bảo mật?
**Scoring caution:** Không coi một mô hình luôn tốt hơn mô hình kia.

### etl_03 — Job chạy hằng ngày để lấy đơn hàng mới. Làm sao chạy lại ngày hôm qua mà không nhân đôi đơn?
**Levels:** fresher, junior
**Objective:** Thiết kế pipeline idempotent.
**Expected points:**
- Khóa nghiệp vụ duy nhất kết hợp UPSERT/MERGE, hoặc ghi đè theo partition ngày.
- Ranh giới ngày/partition và watermark nhất quán.
- Kiểm thử bằng cách chạy lại cùng đầu vào và so sánh checksum hoặc số dòng.
**Follow-up probes:**
- Nếu đơn cũ bị đổi trạng thái sau một ngày thì sao?
- Bạn dùng cửa sổ lookback thế nào?
**Scoring caution:** Không chấp nhận chỉ append mà tuyên bố pipeline idempotent.

### etl_04 — Dữ liệu giao dịch đến muộn 3 ngày khiến dashboard theo ngày bị thiếu. Bạn xử lý thế nào?
**Levels:** fresher, junior
**Objective:** Xử lý dữ liệu đến muộn với event time và xử lý lại có chủ đích.
**Expected points:**
- Phân biệt event time với processing time.
- Xử lý lại các partition bị ảnh hưởng trong cửa sổ lookback.
- Theo dõi độ tươi dữ liệu và cập nhật các bảng phía sau.
**Follow-up probes:**
- Backfill một partition đã publish thì làm thế nào?
- Bạn thông báo dữ liệu tạm thời (provisional) cho người dùng ra sao?
**Scoring caution:** Không coi mọi dữ liệu đến muộn là không hợp lệ.

### etl_05 — Một job xử lý dữ liệu chạy thành công nhưng tổng số liệu sai. Bạn điều tra thế nào?
**Levels:** fresher, junior
**Objective:** Điều tra tính đúng của dữ liệu theo từng bước.
**Expected points:**
- Kiểm tra lineage, độ tươi, mẫu dữ liệu thô và dữ liệu đầu ra.
- So sánh số dòng, khóa, trùng lặp và NULL giữa các bước.
- Khoanh vùng bước biến đổi gây sai và bổ sung kiểm thử dữ liệu.
**Follow-up probes:**
- Nếu nguyên nhân là dữ liệu đến muộn thì sao?
- Bạn thêm data-quality test nào để phát hiện sớm?
**Scoring caution:** Không chấp nhận dựa vào trạng thái "success" của job để coi dữ liệu là đúng.

### etl_06 — Phía upstream đổi schema, pipeline không báo lỗi nhưng kết quả sai. Bạn thiết kế phòng ngừa ra sao?
**Levels:** junior
**Objective:** Bảo vệ pipeline trước thay đổi schema âm thầm.
**Expected points:**
- Kiểm tra schema/contract tại ranh giới nhận dữ liệu.
- Kiểm tra drift và chất lượng, lineage và cảnh báo.
- Cách ly dữ liệu lỗi, quản lý phiên bản và có khả năng rollback.
**Follow-up probes:**
- Bạn kiểm thử thay đổi từ nullable sang bắt buộc thế nào?
- Khi nào cần dừng publish dữ liệu?
**Scoring caution:** Không dùng việc tác vụ chạy thành công làm bằng chứng dữ liệu đúng.

## Scoring Rubric

- technical_accuracy: 0.35 — Luồng pipeline và grain đúng; hiểu đúng ETL/ELT, watermark, event time.
- completeness: 0.30 — Đối chiếu expected points, đặc biệt rerun, backfill và kiểm tra chất lượng.
- reasoning: 0.25 — Giải thích idempotency, xử lý dữ liệu đến muộn và vận hành có căn cứ.
- practical_examples: 0.10 — Ví dụ thực tế về pipeline và cách quan sát, khắc phục.

## Positive Signals

- Nêu khóa nghiệp vụ và chính sách xử lý dữ liệu đến muộn.
- Đặt data-quality gate trước khi publish.
- Pipeline chạy lại và backfill được an toàn.

## Pitfalls

- Publish dữ liệu sai và chỉ dựa vào cảnh báo sau đó.
- Không thể chạy lại một ngày một cách an toàn.
- Âm thầm loại bỏ bản ghi lỗi.

## References

- Apache Airflow documentation — https://airflow.apache.org/docs/
- dbt, Data tests — https://docs.getdbt.com/docs/build/data-tests

## Changelog

- 1.0.0 (2026-11-03): Chuyển đổi từ IntervAI Skill Library v1.0, thêm câu ETL/ELT và câu điều tra số liệu sai; chờ review.
