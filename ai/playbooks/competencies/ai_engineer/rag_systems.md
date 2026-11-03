---
id: rag_systems
kind: competency_skill
version: 1.0.0
assessment: question
levels: [intern, fresher, junior]
keywords: [rag, retrieval-augmented generation, retrieval, embedding, vector database, chunking, bm25, hybrid search, reranking, reranker, faiss, qdrant, pgvector, llamaindex, langchain]
status: draft
---

# RAG Systems

## Learning Objectives

- Giải thích vì sao cần RAG và các thành phần của pipeline: ingestion, chunking, embedding, indexing, retrieval, generation.
- Phân biệt dense, sparse (BM25) và hybrid retrieval; biết khi nào reranking đáng giá.
- Đánh giá tách biệt chất lượng retrieval và chất lượng câu trả lời; phân biệt có trích dẫn với trích dẫn đúng.
- Thiết kế RAG cho dữ liệu thật: cập nhật index, phân quyền tài liệu, latency và chi phí.

## Core Knowledge

**Mục đích.** RAG truy xuất các đoạn tài liệu liên quan rồi đưa vào ngữ cảnh để LLM trả lời dựa trên chúng. RAG phù hợp khi tri thức thay đổi thường xuyên, là dữ liệu riêng/nội bộ, hoặc cần trích dẫn nguồn; nó giảm nhưng không loại bỏ hoàn toàn việc mô hình bịa nội dung. Fine-tuning phù hợp hơn để đổi hành vi, định dạng hay văn phong; kém linh hoạt để cập nhật kiến thức và khó truy ngược nguồn.

**Ingestion và chunking.** Tài liệu được làm sạch rồi chia đoạn theo kích thước cố định có overlap, hoặc theo cấu trúc (tiêu đề, mục, đoạn văn). Chunk quá nhỏ mất ngữ cảnh; quá lớn làm loãng embedding, tốn context và chi phí. Mỗi chunk cần metadata và ID tài liệu ổn định để lọc, cập nhật và trích dẫn.

**Embedding và index.** Truy vấn và tài liệu phải mã hóa bằng cùng một mô hình embedding (hoặc cặp encoder tương thích). Chỉ mục ANN như HNSW hoặc IVF đánh đổi một phần recall lấy tốc độ. Đổi mô hình embedding thì phải tạo lại toàn bộ index.

**Dense, sparse và hybrid.** Dense retrieval bắt ngữ nghĩa và cách diễn đạt khác nhau; sparse (BM25) mạnh với từ khóa chính xác, mã lỗi, tên riêng. Hybrid gộp hai danh sách bằng Reciprocal Rank Fusion (dựa trên thứ hạng) hoặc chuẩn hóa điểm rồi cộng có trọng số, vì điểm thô hai bên không cùng thang đo; cần khử trùng lặp. Hybrid không mặc nhiên tốt hơn — phải đo trên bộ truy vấn của chính hệ thống.

**Reranking.** Cross-encoder đọc đồng thời truy vấn và từng đoạn để chấm lại top-N; chính xác hơn bi-encoder nhưng chậm hơn nhiều, nên chỉ dùng cho N nhỏ. Đổi lại độ chính xác ở top-K là latency và chi phí.

**Generation và trích dẫn.** Prompt yêu cầu trả lời dựa trên ngữ cảnh, nói rõ khi không đủ thông tin và trích dẫn nguồn. Trích dẫn phải gắn với đoạn thực sự hỗ trợ từng ý; có trích dẫn không đồng nghĩa trích dẫn đúng. Đưa quá nhiều đoạn có thể gây nhiễu, làm mô hình bỏ sót thông tin giữa ngữ cảnh dài và tăng chi phí.

**Đánh giá.** Retrieval: Recall@K, Precision@K, MRR, nDCG trên bộ truy vấn có nhãn. Generation: faithfulness/groundedness (câu trả lời có được ngữ cảnh hỗ trợ không) và độ đúng của câu trả lời. LLM-as-judge cần đối chiếu với nhãn người trên một mẫu.

**Vận hành.** Index phải cập nhật tăng dần, xử lý xóa và phiên bản tài liệu; lọc quyền truy cập trước khi đưa tài liệu vào ngữ cảnh; nội dung tài liệu có thể chứa prompt injection.

## Level Guidance

### Intern

- Giải thích được RAG là gì, vì sao cần và các bước chính của pipeline.
- Hiểu embedding và tìm kiếm tương đồng ở mức khái niệm; phân biệt với tìm theo từ khóa.

### Fresher

- Thiết kế pipeline RAG cho một bộ tài liệu cụ thể: chunking, embedding, top-K, hybrid và rerank.
- Biết Recall@K/MRR và tách đánh giá retrieval với generation.

### Junior

- Chẩn đoán lỗi có hệ thống, thiết kế cập nhật index, phân quyền tài liệu.
- Cân bằng chất lượng – latency – chi phí và giám sát khi chạy thật.

## Question Seeds

### rag_01 — RAG là gì, và khi nào nên dùng RAG thay vì chỉ gọi thẳng LLM?
**Levels:** intern, fresher
**Objective:** Hiểu mục đích của RAG, các bước chính và giới hạn của nó.
**Expected points:**
- LLM chỉ biết tri thức đến thời điểm huấn luyện và không biết dữ liệu riêng/nội bộ.
- RAG truy xuất đoạn tài liệu liên quan và đưa vào ngữ cảnh để mô hình trả lời dựa trên đó.
- Các bước chính: chia đoạn, tạo embedding, lưu index, truy xuất top-K, sinh câu trả lời.
- Hữu ích cho kiến thức riêng hoặc cập nhật thường xuyên, có thể trích dẫn nguồn; không đảm bảo hết bịa nội dung.
**Follow-up probes:**
- Nếu không tìm thấy tài liệu liên quan thì hệ thống nên làm gì?
- Có cần RAG cho một phép tính đơn giản không?
**Scoring caution:** Không chấp nhận khẳng định RAG đảm bảo câu trả lời luôn đúng.

### rag_02 — Tìm kiếm theo từ khóa và tìm kiếm theo embedding khác nhau thế nào?
**Levels:** intern, fresher
**Objective:** Phân biệt sparse retrieval và dense retrieval.
**Expected points:**
- Tìm theo từ khóa (BM25, TF-IDF) khớp từ ngữ xuất hiện trong văn bản; mạnh với tên riêng, mã, thuật ngữ chính xác.
- Tìm theo embedding so sánh vector ngữ nghĩa (ví dụ cosine similarity); tìm được đoạn diễn đạt khác nhưng cùng ý.
- Embedding có thể bỏ sót từ khóa hiếm hoặc mã lỗi; từ khóa bỏ sót từ đồng nghĩa và cách diễn đạt khác.
- Có thể kết hợp hai cách (hybrid retrieval).
**Follow-up probes:**
- Cho một ví dụ truy vấn mà tìm theo từ khóa tốt hơn embedding.
- Vì sao truy vấn và tài liệu phải dùng cùng một mô hình embedding?
**Scoring caution:** Không chấp nhận "embedding luôn tốt hơn từ khóa".

### rag_03 — Bạn sẽ chia đoạn (chunking) tài liệu thế nào cho một chatbot hỏi đáp nội quy công ty?
**Levels:** fresher, junior
**Objective:** Hiểu tác động của chunking lên retrieval và chọn cấu hình bằng thí nghiệm.
**Expected points:**
- Chunk quá nhỏ mất ngữ cảnh; quá lớn làm loãng embedding, tốn context và chi phí.
- Chia theo cấu trúc tài liệu thường tốt hơn cắt cứng theo số ký tự; dùng overlap để không cắt đứt ý.
- Lưu metadata (tên tài liệu, mục, ngày hiệu lực) để lọc và trích dẫn.
- Chọn kích thước bằng thí nghiệm trên bộ câu hỏi mẫu (ví dụ đo Recall@K).
**Follow-up probes:**
- Bạn đo thế nào để biết cách chunking mới tốt hơn cách cũ?
- Bảng biểu hoặc danh sách dài trong tài liệu thì xử lý ra sao?
**Scoring caution:** Không chấm cao một kích thước chunk "chuẩn" nếu không có cách kiểm chứng.

### rag_04 — Khi nào nên kết hợp dense và sparse retrieval, và bạn gộp kết quả hai bên thế nào?
**Levels:** fresher, junior
**Objective:** Hiểu trade-off của hybrid retrieval và cách chứng minh cải tiến bằng dữ liệu.
**Expected points:**
- Dense mạnh về ngữ nghĩa; sparse mạnh với từ khóa chính xác, tên riêng, mã; hybrid bù điểm yếu cho nhau.
- Gộp bằng Reciprocal Rank Fusion hoặc chuẩn hóa điểm rồi cộng có trọng số, vì điểm thô hai bên không cùng thang đo; khử trùng lặp.
- Có thể thêm cross-encoder reranker cho top-N để tăng độ chính xác, đổi lại latency.
- Chứng minh bằng thí nghiệm trên bộ truy vấn có nhãn, so với từng retriever riêng lẻ.
**Follow-up probes:**
- Vì sao không nên cộng trực tiếp điểm cosine và điểm BM25?
- Khi nào việc thêm reranker là đáng?
**Scoring caution:** Không coi việc nối hai danh sách mà không khử trùng lặp là fusion đúng.

### rag_05 — Chatbot RAG trích dẫn nguồn đầy đủ nhưng câu trả lời vẫn sai. Bạn debug từ đâu?
**Levels:** fresher, junior
**Objective:** Phân tích lỗi theo từng tầng và kiểm tra trích dẫn có thực sự hỗ trợ câu trả lời.
**Expected points:**
- Tách lỗi theo tầng: chunking, retrieval, reranking, generation.
- Kiểm tra đoạn được trích dẫn có thực sự hỗ trợ từng ý trong câu trả lời (faithfulness/groundedness).
- Đo Recall@K trên bộ câu hỏi có nhãn để biết đoạn đúng có được truy xuất không.
- Nếu retrieval đúng mà vẫn sai: xem prompt, độ dài ngữ cảnh, mô hình bỏ qua ngữ cảnh hoặc bịa thêm.
**Follow-up probes:**
- Nếu truy xuất đúng tài liệu nhưng thiếu đoạn quan trọng thì sao?
- Bạn kiểm tra groundedness bằng người hay bằng LLM-as-judge, và kiểm soát độ tin cậy thế nào?
**Scoring caution:** Có trích dẫn không đồng nghĩa trích dẫn đúng.

### rag_06 — Thiết kế RAG cho 1.000 tài liệu nội bộ thay đổi hằng ngày, mỗi nhóm người dùng có quyền truy cập khác nhau.
**Levels:** junior
**Objective:** Thiết kế indexing tăng dần, phân quyền và giám sát cho RAG dùng thật.
**Expected points:**
- Pipeline index tăng dần, có phiên bản tài liệu và xử lý xóa/cập nhật để không còn chunk cũ.
- Lọc theo quyền truy cập trước khi truy xuất hoặc trước khi đưa vào ngữ cảnh.
- Theo dõi chất lượng retrieval, groundedness, latency và có khả năng rollback index.
**Follow-up probes:**
- Làm sao ngăn tài liệu không có quyền lọt vào ngữ cảnh?
- Khi một tài liệu được cập nhật, bạn xử lý các chunk cũ thế nào?
**Scoring caution:** Không chấp nhận lọc quyền sau khi LLM đã đọc tài liệu.

### rag_07 — Khi đưa RAG vào sử dụng thật, bạn theo dõi chất lượng và tối ưu latency, chi phí ra sao?
**Levels:** junior
**Objective:** Vận hành RAG: đo theo từng bước, tối ưu có căn cứ và giám sát chất lượng.
**Expected points:**
- Đo latency theo từng bước (embedding truy vấn, retrieval, rerank, LLM) để tìm nút thắt.
- Giảm chi phí/latency: bớt số đoạn đưa vào prompt, cache truy vấn lặp lại, giới hạn reranker ở top-N nhỏ.
- Theo dõi tỷ lệ "không tìm thấy thông tin", phản hồi người dùng và review định kỳ một mẫu log.
**Follow-up probes:**
- Nếu cache trả về câu trả lời cũ sau khi tài liệu đã cập nhật thì xử lý thế nào?
- Bạn đặt ngưỡng cảnh báo chất lượng dựa trên dữ liệu gì?
**Scoring caution:** Không tối ưu latency bằng cách hy sinh chất lượng mà không đo.

## Scoring Rubric

- technical_accuracy: 0.40 — Đúng cơ chế RAG, loại retrieval và metric; không nhầm metric retrieval với chất lượng câu trả lời.
- completeness: 0.25 — Đối chiếu expected points của từng câu.
- reasoning: 0.20 — Thiết kế/chẩn đoán retrieval có kiểm chứng; nêu trade-off chất lượng, latency, chi phí.
- practical_examples: 0.15 — Ví dụ từ đồ án hoặc dự án RAG đã làm, kể cả quy mô nhỏ.

## Positive Signals

- Đề xuất đo bằng bộ truy vấn có nhãn trước khi khẳng định cải tiến.
- Tách bạch lỗi do retrieval và lỗi do generation; phân biệt có trích dẫn với trích dẫn đúng.
- Nhắc tới metadata, cập nhật index và phân quyền tài liệu khi nói về hệ thống thật.
- Biết để hệ thống nói "không đủ thông tin" thay vì bịa.

## Pitfalls

- Cho rằng hybrid hoặc reranking luôn tốt hơn mà không có dữ liệu.
- Cộng trực tiếp điểm BM25 với cosine similarity; coi cosine score là độ đúng.
- Đánh giá RAG chỉ bằng vài câu hỏi thử thủ công hoặc trên chính dữ liệu đã dùng để chỉnh.
- Đồng nhất RAG với việc "dùng vector database".

## References

- Lewis et al. (2020), Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks — https://arxiv.org/abs/2005.11401
- Cormack, Clarke & Büttcher (2009), Reciprocal Rank Fusion — https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf
- Liu et al. (2023), Lost in the Middle: How Language Models Use Long Contexts — https://arxiv.org/abs/2307.03172
- Es et al. (2023), RAGAS: Automated Evaluation of Retrieval Augmented Generation — https://arxiv.org/abs/2309.15217
- Qdrant documentation, Hybrid Queries — https://qdrant.tech/documentation/concepts/hybrid-queries/
- Manning, Raghavan & Schütze, Introduction to Information Retrieval — https://nlp.stanford.edu/IR-book/

## Changelog

- 1.0.0 (2026-11-03): Gộp bản nháp ban đầu với IntervAI Skill Library v1.0; chờ review.
