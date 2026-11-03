---
id: deep_learning
kind: competency_skill
version: 1.0.0
assessment: question
levels: [intern, fresher, junior]
keywords: [deep learning, pytorch, tensorflow, keras, neural network, cnn, transformer, fine-tuning, transfer learning, backpropagation, gpu, quantization, onnx]
status: draft
---

# Deep Learning & Training

## Learning Objectives

- Hiểu vòng lặp huấn luyện mạng nơ-ron và vai trò của loss, gradient, optimizer.
- Đọc learning curve, chẩn đoán vấn đề huấn luyện và chọn transfer learning hợp lý.
- Tối ưu inference có kiểm chứng chất lượng.

## Core Knowledge

- Một bước huấn luyện: forward tạo dự đoán → tính loss → backward tính gradient → optimizer cập nhật tham số; xóa gradient cũ (zero_grad) để không tích lũy ngoài ý muốn.
- Chế độ train/eval khác nhau với dropout và batch normalization; khi suy luận dùng chế độ eval và tắt tính gradient để tiết kiệm bộ nhớ.
- Learning rate, batch size, normalization và regularization ảnh hưởng tốc độ hội tụ và độ ổn định.
- CNN học đặc trưng cục bộ; Transformer dùng attention để trao đổi thông tin giữa các token, chi phí tăng theo độ dài chuỗi.
- Fine-tuning mô hình pretrained tiết kiệm dữ liệu và tính toán; cần cân nhắc đóng băng/mở các lớp và đánh giá lệch phân phối.
- Tối ưu inference (batching, quantization, export ONNX…) phải đo cả latency lẫn chất lượng trên cùng tập kiểm thử.

## Level Guidance

### Intern

- Giải thích loss, gradient descent, epoch, batch và vòng lặp huấn luyện cơ bản.

### Fresher

- Debug learning curve, chọn chiến lược fine-tune hay đóng băng backbone, đánh giá theo lớp.

### Junior

- Thiết kế thí nghiệm ablation, tối ưu inference với giới hạn tài nguyên và kiểm chứng không giảm chất lượng.

## Question Seeds

### dl_01 — Trong một vòng lặp huấn luyện PyTorch, forward, loss, backward và optimizer lần lượt làm gì?
**Levels:** intern, fresher
**Objective:** Hiểu cơ chế một bước huấn luyện mạng nơ-ron.
**Expected points:**
- Forward tạo dự đoán và tính loss so với nhãn.
- Backward tính gradient của loss theo các tham số.
- Optimizer cập nhật tham số; zero_grad xóa gradient cũ để tránh tích lũy ngoài ý muốn.
**Follow-up probes:**
- Nếu quên chuyển mô hình sang chế độ eval khi validate thì có thể xảy ra gì?
- Vì sao cần tắt tính gradient khi suy luận?
**Scoring caution:** Không yêu cầu nhớ đúng cú pháp; chấm hiểu cơ chế.

### dl_02 — Train loss giảm đều nhưng validation loss bắt đầu tăng sau vài epoch. Bạn suy luận và thử gì?
**Levels:** intern, fresher
**Objective:** Đọc learning curve và đề xuất biện pháp có kiểm chứng.
**Expected points:**
- Đây là dấu hiệu overfitting, cần xác nhận lại bằng learning curve và cách chia dữ liệu.
- Kiểm tra lại split và augmentation.
- Thử early stopping, regularization/dropout hoặc tăng dữ liệu phù hợp.
**Follow-up probes:**
- Làm sao biết augmentation không làm sai nhãn?
- Vì sao dropout có thể giúp?
**Scoring caution:** Không khẳng định overfitting chỉ từ một điểm đo duy nhất.

### dl_03 — Bạn có vài nghìn ảnh đã gắn nhãn và muốn xây bộ phân loại. Bạn bắt đầu thế nào?
**Levels:** fresher, junior
**Objective:** Chọn transfer learning và quy trình đánh giá hợp lý khi ít dữ liệu.
**Expected points:**
- Bắt đầu từ mô hình pretrained làm baseline và xác định cách chia tập.
- Fine-tune hoặc đóng băng backbone, có giải thích lựa chọn.
- Đánh giá theo từng lớp/nhóm dữ liệu trên tập test độc lập.
**Follow-up probes:**
- Khi nào nên mở thêm nhiều lớp để fine-tune?
- Bạn theo dõi VRAM và throughput ra sao?
**Scoring caution:** Không mặc định huấn luyện từ đầu luôn tốt hơn.

### dl_04 — Mô hình cho kết quả tốt nhưng suy luận trên CPU quá chậm. Nêu kế hoạch cải thiện có kiểm chứng.
**Levels:** junior
**Objective:** Tối ưu inference dựa trên profiling và giữ chất lượng.
**Expected points:**
- Profile thời gian tiền xử lý, tính toán mô hình và hậu xử lý để tìm nút thắt.
- Thử batching, quantization hoặc export sang runtime phù hợp.
- So sánh latency và chất lượng trên cùng bộ kiểm thử trước và sau.
**Follow-up probes:**
- Quantization có thể làm giảm chất lượng ở nhóm dữ liệu nào?
- Bạn chọn P95 latency hay throughput làm mục tiêu, vì sao?
**Scoring caution:** Không hứa con số tốc độ cụ thể khi chưa benchmark.

### dl_05 — Thiết kế thí nghiệm ablation để biết một kỹ thuật (ví dụ augmentation mới) có thực sự giúp mô hình hay không.
**Levels:** fresher, junior
**Objective:** Thiết kế thí nghiệm so sánh công bằng và có tính đến độ biến thiên.
**Expected points:**
- Giữ nguyên dữ liệu, chia tập và cấu hình; chỉ thay đổi một yếu tố.
- Chạy nhiều seed hoặc nhiều lần để thấy độ biến thiên, không kết luận từ một lần chạy.
- So sánh trên cùng tập đánh giá, xem cả metric tổng và theo nhóm.
**Follow-up probes:**
- Nếu chênh lệch nhỏ hơn độ biến thiên giữa các seed thì bạn kết luận gì?
- Bạn ghi lại cấu hình thí nghiệm thế nào để tái lập?
**Scoring caution:** Không chấp nhận so sánh hai mô hình trên các tập chia khác nhau.

## Scoring Rubric

- technical_accuracy: 0.40 — Nguyên lý huấn luyện đúng (gradient, chế độ train/eval, overfitting, transfer learning).
- completeness: 0.25 — Đối chiếu expected points của từng câu.
- reasoning: 0.25 — Thiết kế thí nghiệm và chẩn đoán có kiểm chứng, không kết luận từ một lần chạy.
- practical_examples: 0.10 — Tính khả thi và ví dụ từ việc đã làm.

## Positive Signals

- Phân biệt vấn đề do năng lực mô hình với vấn đề do dữ liệu.
- Có baseline và ablation, không kết luận từ một lần chạy.
- Đo chất lượng song song với tốc độ khi tối ưu.

## Pitfalls

- Không biết sự khác nhau giữa chế độ train và eval.
- So sánh các mô hình trên các tập chia khác nhau.
- Tăng kích thước mô hình trước khi kiểm tra dữ liệu.

## References

- PyTorch Tutorials — https://docs.pytorch.org/tutorials/
- Dive into Deep Learning — https://d2l.ai/

## Changelog

- 1.0.0 (2026-11-03): Chuyển đổi từ IntervAI Skill Library v1.0, thêm câu ablation; chờ review.
