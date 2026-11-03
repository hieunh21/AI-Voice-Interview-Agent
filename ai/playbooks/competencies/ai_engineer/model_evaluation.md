---
id: model_evaluation
kind: competency_skill
version: 1.0.0
assessment: question
levels: [intern, fresher, junior]
keywords: [evaluation, metrics, benchmark, precision, recall, f1, llm-as-judge, ablation, a/b test, mlflow, langsmith, ragas, monitoring]
status: draft
---

# Model & LLM Application Evaluation

## Learning Objectives

- Thiết kế benchmark đáng tin: ground truth, baseline, chia tập và metric phù hợp tác vụ.
- Phối hợp metric offline, đánh giá của người và chỉ số khi chạy thật.
- Đánh giá ứng dụng LLM, bao gồm LLM-as-judge và kiểm soát thiên lệch.

## Core Knowledge

- Ground truth định nghĩa theo tác vụ; cần quản lý phiên bản dữ liệu, prompt và mô hình để kết quả tái lập được.
- Precision = trong các dự đoán dương, bao nhiêu đúng; recall = trong các mẫu dương thật, bắt được bao nhiêu. F1 cân bằng hai giá trị; macro/micro F1 chọn theo mục tiêu.
- Retrieval dùng Recall@K, MRR, nDCG; hỏi đáp sinh văn bản cần groundedness và correctness.
- LLM-as-judge có thiên lệch (vị trí, độ dài, văn phong); cần rubric cụ thể, đối chiếu một phần với nhãn người, chấm mù danh tính khi có thể.
- Ablation chỉ thay một yếu tố chính, dùng cùng tập đánh giá và quan tâm độ bất định của kết quả.
- Khi chạy thật cần theo dõi theo nhóm lỗi, latency P95, chi phí mỗi request, không chỉ điểm trung bình; phát hành dần (canary, feature flag) và có regression set.

## Level Guidance

### Intern

- Biết metric cơ bản, cách dựng tập test và phân tích lỗi đơn giản.

### Fresher

- Thiết kế benchmark/ablation có baseline, kiểm tra bằng người và đo cả latency.

### Junior

- Phân tích trade-off giữa các metric, drift, độ tin cậy và quy trình phát hành an toàn.

## Question Seeds

### eval_01 — Để biết một mô hình phân loại có tốt hay không, bạn đánh giá qua những bước nào?
**Levels:** intern, fresher
**Objective:** Nắm quy trình đánh giá cơ bản từ ground truth đến phân tích lỗi.
**Expected points:**
- Xác định tác vụ và ground truth.
- Chia train/validation/test phù hợp.
- Chọn metric theo mục tiêu và xem lỗi theo từng nhóm dữ liệu.
**Follow-up probes:**
- Khi nào accuracy không đủ?
- Bạn chọn baseline đơn giản nào để so sánh?
**Scoring caution:** Không lẫn lộn loss huấn luyện với metric mục tiêu.

### eval_02 — Precision và recall khác nhau thế nào? Cho ví dụ khi nào nên ưu tiên cái nào.
**Levels:** intern, fresher
**Objective:** Hiểu đúng định nghĩa và lựa chọn metric theo chi phí lỗi.
**Expected points:**
- Precision: trong các dự đoán dương, tỷ lệ đúng; recall: trong các mẫu dương thật, tỷ lệ bắt được.
- Ưu tiên recall khi bỏ sót đắt (ví dụ sàng lọc bệnh); ưu tiên precision khi báo nhầm đắt (ví dụ lọc spam chặn nhầm thư quan trọng).
- Thay đổi ngưỡng tạo ra đánh đổi giữa precision và recall.
**Follow-up probes:**
- F1 dùng khi nào, và có hạn chế gì?
- Khi lớp dương rất hiếm, đường PR có ích gì hơn ROC?
**Scoring caution:** Không chấp nhận định nghĩa đảo ngược precision và recall.

### eval_03 — Bạn thêm reranker vào hệ thống RAG. Làm sao chứng minh nó tốt hơn baseline?
**Levels:** fresher, junior
**Objective:** Thiết kế so sánh có kiểm soát và xem xét cả chất lượng lẫn chi phí.
**Expected points:**
- Giữ nguyên tập truy vấn và nhãn liên quan cho cả hai cấu hình.
- So sánh metric retrieval@K và latency.
- Phân tích cả trường hợp cải thiện lẫn trường hợp tệ đi.
**Follow-up probes:**
- Nếu recall@K tăng nhưng độ đúng của câu trả lời giảm thì sao?
- Bạn đánh giá độ bất định của kết quả thế nào?
**Scoring caution:** Không chấp nhận kết luận từ vài câu demo dễ.

### eval_04 — Bạn dùng LLM-as-judge để chấm câu trả lời phỏng vấn. Làm sao giảm thiên lệch?
**Levels:** fresher, junior
**Objective:** Kiểm soát độ tin cậy và công bằng của LLM-as-judge.
**Expected points:**
- Rubric cụ thể, yêu cầu trích dẫn bằng chứng từ câu trả lời.
- So sánh một tập với nhãn của người và đo mức đồng thuận.
- Ẩn danh tính ứng viên, chấm lặp nhiều lần để kiểm tra độ ổn định.
**Follow-up probes:**
- Nếu hai lần chấm cùng một câu ra kết quả khác nhau nhiều thì sao?
- Làm sao tránh thiên lệch với cách nói hay phương ngữ?
**Scoring caution:** Không dùng phát âm, giới tính hay giọng vùng miền để suy ra trình độ.

### eval_05 — Sau khi đổi mô hình, độ chính xác tăng nhưng thời gian phản hồi tăng gấp đôi. Bạn quyết định thế nào?
**Levels:** fresher, junior
**Objective:** Cân bằng chất lượng và latency dựa trên đo đạc và mục tiêu dịch vụ.
**Expected points:**
- Tách mục tiêu chất lượng và độ trễ, đo trên cùng tập kiểm thử với baseline.
- Profile thời gian theo từng giai đoạn để tìm phần tốn kém.
- Thử tối ưu rồi quyết định theo SLO và giá trị thực tế của mức tăng chất lượng.
**Follow-up probes:**
- P50 tốt nhưng P95 xấu thì xử lý ra sao?
- Có cách nào dùng mô hình lớn chỉ cho một phần request không?
**Scoring caution:** Không bắt buộc một mô hình cụ thể; chấm cách ra quyết định.

### eval_06 — Một agent đạt 90% tỷ lệ hoàn thành khi đánh giá offline nhưng thất bại nhiều khi chạy thật. Bạn điều tra và phát hành lại ra sao?
**Levels:** junior
**Objective:** Đối chiếu offline với thực tế và phát hành có kiểm soát.
**Expected points:**
- Phân tích lệch phân phối giữa tập offline và dữ liệu thật, cùng lỗi gọi tool.
- Đo tỷ lệ lỗi, timeout, chi phí và latency P95 khi chạy thật.
- Phát hành dần bằng canary/feature flag và bổ sung regression set từ lỗi thật.
**Follow-up probes:**
- Bộ test cần mở rộng theo hướng nào?
- Khi nào nên rollback?
**Scoring caution:** Không coi 90% trên dữ liệu tổng hợp là bảo đảm khi chạy thật.

## Scoring Rubric

- technical_accuracy: 0.35 — Chọn và hiểu đúng metric; không nhầm metric chất lượng với metric vận hành.
- completeness: 0.25 — Đối chiếu expected points của từng câu.
- reasoning: 0.25 — Tính chặt chẽ của thí nghiệm: baseline, chia tập, độ bất định, hiệu chuẩn bằng người.
- practical_examples: 0.15 — Gắn với lỗi và ràng buộc thực tế khi chạy thật.

## Positive Signals

- Phân biệt metric chất lượng và metric vận hành.
- Thành thật về giới hạn của ground truth và kích thước mẫu.
- Phân tích cả trường hợp tốt lên và tệ đi.

## Pitfalls

- Đánh giá bằng chính các câu đã dùng để chỉnh prompt.
- Nêu tỷ lệ chính xác tuyệt đối mà không nói kích thước mẫu.
- Tin tuyệt đối vào LLM-as-judge mà không đối chiếu với người.

## References

- scikit-learn, Model evaluation — https://scikit-learn.org/stable/modules/model_evaluation.html
- Zheng et al. (2023), Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena — https://arxiv.org/abs/2306.05685

## Changelog

- 1.0.0 (2026-11-03): Chuyển đổi từ IntervAI Skill Library v1.0, thêm câu precision/recall và câu chất lượng–latency; chờ review.
