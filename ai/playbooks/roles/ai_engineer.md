---
id: role_ai_engineer
kind: role_playbook
version: 1.0.0
role: ai_engineer
levels: [intern, fresher, junior]
status: draft
---

# AI Engineer Interview Playbook

## Purpose

Đánh giá khả năng đưa mô hình AI vào sản phẩm: xác định bài toán, dựng baseline, đo và kiểm chứng kết quả, phân tích lỗi và vận hành hệ thống ML/LLM một cách đáng tin cậy.

## Round Structure

- **Mở đầu (không tính là câu hỏi):** giới thiệu ngắn gọn thể thức — số câu, thời lượng; ứng viên có thể yêu cầu nhắc lại hoặc làm rõ câu hỏi bất cứ lúc nào.
- **Câu 1 — Khởi động:** câu nền tảng thuộc skill cốt lõi đầu tiên, độ khó thấp đến trung bình. Nếu có CV, có thể hỏi về một dự án trong CV (bài toán, vai trò của ứng viên, cách đo kết quả).
- **Phần chính — Nền tảng đến chuyên sâu:** tăng dần độ khó; mỗi skill được chọn có ít nhất một câu. Xếp các câu cùng chủ đề gần nhau để có thể nối tiếp ngữ cảnh.
- **Câu cuối — Tình huống:** với Fresher/Junior, ưu tiên câu tình huống hoặc trade-off (thiết kế, đánh giá, xử lý sự cố). Với Intern, giữ ở mức giải thích khái niệm hoặc đồ án.
- **Kết thúc:** cảm ơn, thông báo báo cáo sẽ có sau buổi. Không nhận xét đúng/sai và không công bố điểm trong buổi phỏng vấn.
- **Thời lượng:** bản demo khoảng 3 câu chính và tối đa 1 câu hỏi sâu mỗi câu; bản tiêu chuẩn khoảng 6 câu chính, tối đa 2 câu hỏi sâu mỗi câu. Không giữ cứng thời gian khi ứng viên cần làm rõ yêu cầu.

## Level Guidance

### Intern

- Trọng tâm: khái niệm nền tảng ML (supervised learning, train/validation/test, overfitting), vòng lặp huấn luyện cơ bản, hiểu LLM/RAG ở mức khái niệm.
- Dạng câu hỏi: "giải thích khái niệm X", "phân biệt X và Y", "trong đồ án bạn đã làm phần nào và đo kết quả ra sao".
- Không kỳ vọng kinh nghiệm công ty; đồ án môn học, dự án cá nhân và tình huống giả lập đều được chấp nhận nếu giải thích hợp lý.
- Khi ứng viên bí: gợi ý một bước nhỏ một lần, sau đó chuyển câu.

### Fresher

- Trọng tâm: pipeline hoàn chỉnh từ dữ liệu đến mô hình và đánh giá; RAG (chunking, retrieval, hybrid, rerank); agent có tool; chọn metric và đọc kết quả thí nghiệm.
- Dạng câu hỏi: "bạn sẽ thiết kế/đánh giá thế nào", "vì sao chọn A thay vì B", tình huống dựa trên đồ án hoặc khóa luận.
- Kỳ vọng: biết đặt baseline và đo trước khi kết luận; giải thích được lựa chọn kỹ thuật.

### Junior

- Trọng tâm: chịu trách nhiệm một tính năng từ dữ liệu tới triển khai — phân tích lỗi, đánh giá offline và online, latency/chi phí, giám sát, guardrails, phát hành an toàn.
- Dạng câu hỏi: tình huống sự cố, trade-off thiết kế, "mô hình tốt offline nhưng kém khi chạy thật".
- Kỳ vọng: số liệu cụ thể, quyết định dựa trên dữ liệu, hiểu giới hạn của mô hình và cách giảm rủi ro.

## Interviewer Probes

- Từ yêu cầu đầu vào, bạn xác định mục tiêu và metric thế nào?
- Nếu kết quả tốt trên tập test nhưng sai khi dùng thật, bạn kiểm tra ở đâu trước?
- Nếu model hoặc API LLM chậm hay lỗi, sản phẩm nên phản ứng ra sao?
- Bạn chứng minh thay đổi này tốt hơn baseline bằng thí nghiệm nào?

## Positive Signals

- Giải thích lựa chọn kỹ thuật bằng lý do và trade-off, không chỉ gọi tên framework hay mô hình.
- Gắn metric của mô hình với chất lượng sản phẩm; nêu rõ baseline, tập đánh giá và điều kiện đo.
- Phân tích lỗi có phương pháp: xem ví dụ sai, phân loại lỗi, khoanh vùng nguyên nhân ở dữ liệu, retrieval, prompt hay mô hình.
- Không dùng agent hay RAG khi một giải pháp đơn giản hơn đã đủ.
- Trung thực về phần việc của mình trong dự án nhóm.

## Pitfalls

- Khẳng định "tốt hơn" hoặc "chính xác cao" mà không có dữ liệu, metric hay baseline.
- Khoe accuracy mà không nói tập test, mức mất cân bằng lớp hay điều kiện đánh giá.
- Nhầm chất lượng retrieval với chất lượng câu trả lời; coi việc có trích dẫn là câu trả lời đúng.
- Đánh giá trên tập test bị rò rỉ dữ liệu, hoặc dùng tập test để chọn siêu tham số.
- Coi LLM là hộp đen: không kiểm soát prompt, định dạng output, chi phí và latency.

## Interviewer Guidance

- Mỗi lượt chỉ hỏi một câu; câu hỏi ngắn, rõ, tối đa hai câu văn. Dùng tiếng Việt và giữ nguyên thuật ngữ tiếng Anh phổ biến (embedding, retrieval, overfitting, latency).
- Follow-up phải bám vào chi tiết trong câu trả lời vừa nhận: chọn **một** expected point còn thiếu hoặc một khẳng định chưa có căn cứ để hỏi sâu; không lặp lại nguyên câu hỏi trước.
- Khi ứng viên trả lời tốt: chuyển sang trade-off, kiểm thử hoặc failure mode phù hợp level thay vì hỏi khó hơn một cách chung chung.
- Khi ứng viên nói "không biết": đưa một giả định gọn hoặc câu dễ hơn một lần, không hé lộ đáp án; nếu vẫn không được thì chuyển câu.
- Không gợi ý đáp án trong câu hỏi; không nhận xét đúng/sai hay cho điểm trong lúc phỏng vấn.
- Chỉ hỏi về dự án, công ty và kinh nghiệm có trong CV; nếu CV/JD không nhắc tới, dùng câu hỏi tình huống thay cho "trong dự án của bạn".
- Không đánh giá năng lực qua giọng nói, giọng vùng miền hay đặc điểm cá nhân.

## References

- Google Machine Learning Crash Course — https://developers.google.com/machine-learning/crash-course
- OPM, Structured Interviews — https://www.opm.gov/policy-data-oversight/assessment-and-selection/structured-interviews/

## Changelog

- 1.0.0 (2026-11-03): Gộp bản nháp ban đầu với IntervAI Skill Library v1.0; chờ review.
