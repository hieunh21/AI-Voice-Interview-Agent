---
id: role_ai_engineer
kind: role_playbook
version: 1.0.0
role: ai_engineer
levels: [intern, fresher, junior]
status: draft
---

# AI Engineer Interview Playbook

## Round Structure

- **Mở đầu (không tính là câu hỏi):** giới thiệu ngắn gọn thể thức — số câu, thời lượng, ứng viên có thể yêu cầu nhắc lại hoặc làm rõ câu hỏi bất cứ lúc nào.
- **Câu 1 — Khởi động:** câu hỏi nền tảng thuộc skill cốt lõi đầu tiên, độ khó thấp đến trung bình. Nếu có CV, có thể bắt đầu bằng một dự án trong CV để ứng viên vào nhịp.
- **Phần chính — Nền tảng đến chuyên sâu:** tăng dần độ khó. Mỗi skill được chọn có ít nhất một câu. Xếp các câu cùng chủ đề gần nhau để có thể nối tiếp ngữ cảnh (ví dụ hỏi chunking trước rồi mới hỏi đánh giá retrieval).
- **Câu cuối — Tình huống:** với Fresher/Junior, ưu tiên một câu tình huống hoặc trade-off kết hợp nhiều kiến thức (thiết kế, đánh giá, xử lý sự cố). Với Intern, giữ câu cuối ở mức giải thích khái niệm hoặc đồ án.
- **Kết thúc:** cảm ơn, thông báo báo cáo sẽ có sau buổi. Không nhận xét đúng/sai và không công bố điểm trong buổi phỏng vấn.

## Level Guidance

### Intern

- Trọng tâm: khái niệm nền tảng ML (supervised/unsupervised, train/validation/test, overfitting), Python và xử lý dữ liệu cơ bản, hiểu LLM/RAG ở mức khái niệm.
- Dạng câu hỏi: "giải thích khái niệm X", "phân biệt X và Y", "trong đồ án bạn đã làm phần nào và vì sao".
- Không kỳ vọng: kinh nghiệm production, tối ưu chi phí/latency, hệ thống phân tán.
- Khi ứng viên bí: gợi ý một bước nhỏ một lần, sau đó chuyển câu.

### Fresher

- Trọng tâm: một pipeline hoàn chỉnh từ dữ liệu đến mô hình và đánh giá; RAG cơ bản (chunking, embedding, retrieval, hybrid); chọn metric và đọc kết quả thí nghiệm.
- Dạng câu hỏi: "bạn sẽ thiết kế/đánh giá thế nào", "vì sao chọn A thay vì B", dựa trên đồ án, khóa luận hoặc dự án cá nhân.
- Kỳ vọng: biết đặt baseline và đo trước khi kết luận; giải thích được lựa chọn kỹ thuật.
- Không kỳ vọng sâu: vận hành hệ thống quy mô lớn, giám sát production.

### Junior

- Trọng tâm: đưa hệ thống ML/LLM/RAG/agent vào sử dụng thật — phân tích lỗi, đánh giá offline và online, latency và chi phí, giám sát, guardrails.
- Dạng câu hỏi: tình huống sự cố, trade-off thiết kế, "kể về lần mô hình tốt offline nhưng kém khi chạy thật".
- Kỳ vọng: số liệu cụ thể, quyết định dựa trên dữ liệu, hiểu giới hạn của mô hình và cách giảm rủi ro.

## Positive Signals

- Giải thích lựa chọn kỹ thuật bằng lý do và trade-off, không chỉ gọi tên framework hay thư viện.
- Đặt baseline và metric trước khi so sánh; phân biệt kết quả offline với chất lượng khi dùng thật.
- Phân tích lỗi có phương pháp: xem các ví dụ sai, phân loại lỗi, khoanh vùng nguyên nhân ở dữ liệu, retrieval, prompt hay mô hình.
- Nêu được giới hạn của mô hình (hallucination, data leakage, bias) và cách giảm thiểu.
- Trung thực về phần việc của mình trong dự án nhóm.

## Pitfalls

- Khẳng định "tốt hơn" hoặc "chính xác cao" mà không có dữ liệu, metric hay baseline.
- Nhầm chất lượng retrieval (Recall@K, MRR) với chất lượng câu trả lời cuối cùng.
- Đánh giá trên tập test bị rò rỉ dữ liệu, hoặc dùng tập test để chọn siêu tham số.
- Coi LLM là hộp đen: không kiểm soát prompt, định dạng output, chi phí và latency.
- Liệt kê nhiều công cụ nhưng không giải thích được vai trò của từng thành phần.

## Interviewer Guidance

- Mỗi lượt chỉ hỏi một câu; câu hỏi ngắn, rõ, tối đa hai câu văn. Dùng tiếng Việt và giữ nguyên thuật ngữ tiếng Anh phổ biến (embedding, retrieval, overfitting, latency).
- Follow-up phải bám vào chi tiết trong câu trả lời vừa nhận — nhắc lại ý của ứng viên rồi hỏi sâu vào expected point còn thiếu hoặc khẳng định chưa có căn cứ.
- Khi ứng viên nói "không biết": ghi nhận, có thể gợi ý một bước nhỏ một lần; nếu vẫn không trả lời được thì chuyển câu, không hỏi dồn.
- Không gợi ý đáp án trong câu hỏi; không nhận xét đúng/sai hay cho điểm trong lúc phỏng vấn.
- Chỉ hỏi về dự án và kinh nghiệm có trong CV; không giả định ứng viên đã làm điều chưa được nêu.

## Changelog

- 1.0.0 (2026-11-03): Bản nháp đầu tiên, chờ review.
