---
id: system_design
kind: competency_skill
version: 1.0.0
assessment: question
levels: [intern, fresher, junior]
keywords: [system design, architecture, scalability, cache, redis, message queue, kafka, rabbitmq, celery, microservices, load balancer, docker, kubernetes, observability, slo]
status: draft
---

# Practical System Design

## Learning Objectives

- Thiết kế hệ thống backend vừa đủ cho yêu cầu và tải cụ thể.
- Hiểu caching, hàng đợi, xử lý nền, xử lý lỗi, tính nhất quán và khả năng quan sát.
- Ứng phó sự cố khi chạy thật một cách có ưu tiên.

## Core Knowledge

- Bắt đầu từ yêu cầu chức năng và phi chức năng: lưu lượng, khối lượng dữ liệu, SLO, các trường hợp lỗi.
- Cache tăng tốc đọc nhưng có vấn đề dữ liệu cũ và invalidation; không cache dữ liệu riêng tư dùng chung giữa người dùng.
- Hàng đợi tách xử lý nền khỏi request; consumer cần idempotency, retry có backoff và dead-letter hoặc trạng thái lỗi.
- Tác vụ dài (ví dụ gọi LLM 30 giây) nên chạy nền với trạng thái pending/running/done/failed, client polling hoặc nhận thông báo.
- Scale ngang chỉ hiệu quả khi service không giữ state cục bộ và điểm nghẽn nằm đúng chỗ; đo trước khi scale.
- SLO gồm latency theo percentile, availability, error budget; log/metrics/traces cần liên kết bằng request ID.
- Khi sự cố: đánh giá phạm vi ảnh hưởng, giảm thiệt hại trước (rollback, feature flag), sau đó tìm nguyên nhân gốc và chống tái phát.

## Level Guidance

### Intern

- Mô tả được client – API – database và vai trò từng phần; hiểu cache ở mức khái niệm.

### Fresher

- Thiết kế upload, job chạy nền, cache có lý do; điều tra latency có phương pháp.

### Junior

- Ước lượng tải sơ bộ, failure mode, trade-off nhất quán; xử lý sự cố khi chạy thật.

## Question Seeds

### sys_01 — Mô tả các thành phần của một ứng dụng chat có lưu lịch sử hội thoại.
**Levels:** intern, fresher
**Objective:** Phân lớp hệ thống cơ bản và nơi lưu trạng thái.
**Expected points:**
- Client gọi API; server xử lý logic; database lưu lịch sử hội thoại.
- Tách xác thực người dùng/phiên đăng nhập và kiểm tra quyền đọc hội thoại.
- Không giữ trạng thái duy nhất trong RAM nếu cần khôi phục sau khi server khởi động lại.
**Follow-up probes:**
- Nếu server khởi động lại thì lịch sử còn không?
- Bạn kiểm tra quyền đọc một hội thoại thế nào?
**Scoring caution:** Không yêu cầu microservices cho ứng dụng nhỏ.

### sys_02 — Cache là gì, khi nào nên dùng, và rủi ro của nó là gì?
**Levels:** intern, fresher
**Objective:** Hiểu lợi ích và chi phí của caching.
**Expected points:**
- Cache lưu tạm kết quả đọc nhiều để giảm latency và tải cho database.
- Phù hợp với dữ liệu đọc nhiều, ít thay đổi, chấp nhận được độ trễ cập nhật.
- Rủi ro: dữ liệu cũ, invalidation phức tạp, lộ dữ liệu nếu cache sai phạm vi người dùng.
**Follow-up probes:**
- Khi dữ liệu gốc thay đổi, bạn cập nhật hoặc xóa cache thế nào?
- Khi nhiều key hết hạn cùng lúc thì chuyện gì xảy ra?
**Scoring caution:** Không chấp nhận "thêm cache là luôn nhanh hơn" mà không nói tới tính đúng.

### sys_03 — Thiết kế dịch vụ upload CV và phân tích bằng LLM, mỗi lần phân tích có thể mất 30 giây.
**Levels:** fresher, junior
**Objective:** Thiết kế xử lý nền cho tác vụ dài với trạng thái và retry an toàn.
**Expected points:**
- Lưu file và tạo job chạy nền thay vì giữ request mở.
- Job có trạng thái pending/running/done/failed; client polling hoặc nhận thông báo.
- Retry an toàn, timeout, giới hạn kích thước và loại file.
**Follow-up probes:**
- Nếu người dùng refresh trang giữa chừng thì sao?
- Bạn tránh xử lý trùng cùng một file thế nào?
**Scoring caution:** Không giữ request HTTP mở rất lâu khi không có lý do.

### sys_04 — API tạo báo cáo có P95 latency tăng cao khi chỉ 10 người dùng đồng thời. Bạn điều tra thế nào?
**Levels:** fresher, junior
**Objective:** Tìm điểm nghẽn bằng đo đạc trước khi thay đổi kiến trúc.
**Expected points:**
- Đo thời gian từng thành phần: gọi LLM, database, hàng đợi, mạng.
- Áp dụng giới hạn đồng thời, rate limit hoặc hàng đợi phù hợp.
- Load test để xác nhận điểm nghẽn trước và sau khi sửa.
**Follow-up probes:**
- Nếu API của mô hình áp quota thì sao?
- Bạn hiển thị tiến độ cho người dùng thế nào?
**Scoring caution:** Không kết luận thiếu CPU khi chưa đo.

### sys_05 — Thiết kế thông báo "đã chấm xong" cho người dùng khi worker có thể bị khởi động lại bất kỳ lúc nào.
**Levels:** junior
**Objective:** Thiết kế xử lý bền vững với at-least-once và idempotency.
**Expected points:**
- Lưu trạng thái job bền vững; chấp nhận giao ít nhất một lần và làm consumer idempotent.
- Retry có backoff, dead-letter hoặc trạng thái thất bại.
- Theo dõi metric và đảm bảo không tạo hai báo cáo hay hai thông báo.
**Follow-up probes:**
- "Exactly-once" ở mức nghiệp vụ nên hiểu thế nào?
- Nếu hàng đợi tạm mất kết nối thì sao?
**Scoring caution:** Không phụ thuộc vào biến trong RAM của một process.

### sys_06 — Bản release vừa deploy gây lỗi cho nhiều người dùng. Bạn ưu tiên làm gì trong 15 phút đầu?
**Levels:** junior
**Objective:** Ứng phó sự cố có ưu tiên: giảm thiệt hại trước, tìm nguyên nhân sau.
**Expected points:**
- Đánh giá phạm vi ảnh hưởng và thông báo cho các bên liên quan.
- Cân nhắc rollback hoặc tắt feature flag một cách an toàn.
- Ghi nhận diễn biến sự cố, xác minh bản sửa và lên kế hoạch postmortem.
**Follow-up probes:**
- Khi nào không nên rollback (ví dụ đã có migration dữ liệu)?
- Bạn thêm regression test hoặc giám sát gì để chống tái phát?
**Scoring caution:** Không chấp nhận chỉ "restart service" mà không kiểm tra nguyên nhân.

## Scoring Rubric

- technical_accuracy: 0.30 — Thành phần và cơ chế đúng (cache, hàng đợi, xử lý nền, SLO).
- completeness: 0.25 — Đối chiếu expected points của từng câu.
- reasoning: 0.35 — Làm rõ yêu cầu, xử lý lỗi và tính nhất quán, trade-off; đo trước khi scale.
- practical_examples: 0.10 — Khả năng vận hành và quan sát thực tế.

## Positive Signals

- Bắt đầu từ thiết kế đơn giản và nói rõ điều kiện cần scale.
- Nêu cách kiểm chứng SLO và giám sát.
- Nghĩ tới failure mode và cách phục hồi.

## Pitfalls

- Đề xuất microservices theo thói quen khi chưa có nhu cầu.
- Không giải thích tính nhất quán dữ liệu và retry.
- Scale hạ tầng trước khi đo điểm nghẽn.

## References

- Google SRE Book — https://sre.google/sre-book/table-of-contents/
- AWS Well-Architected, Reliability Pillar — https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html

## Changelog

- 1.0.0 (2026-11-03): Chuyển đổi từ IntervAI Skill Library v1.0, thêm câu cache và câu sự cố release; chờ review.
