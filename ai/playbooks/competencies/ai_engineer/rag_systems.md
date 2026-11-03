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

- Giải thích vì sao cần RAG và các thành phần của một pipeline RAG: ingestion, chunking, embedding, indexing, retrieval, generation.
- Phân biệt dense, sparse (BM25) và hybrid retrieval; biết khi nào reranking đáng giá.
- Đánh giá tách biệt chất lượng retrieval và chất lượng câu trả lời, dùng đúng metric cho từng tầng.
- Phân tích lỗi và cân bằng chất lượng – latency – chi phí khi đưa RAG vào sử dụng thật.

## Core Knowledge

**Mục đích.** RAG bổ sung tri thức bên ngoài vào ngữ cảnh của LLM tại thời điểm trả lời: truy xuất các đoạn tài liệu liên quan rồi đưa vào prompt để mô hình trả lời dựa trên chúng. RAG phù hợp khi tri thức thay đổi thường xuyên, là dữ liệu riêng/nội bộ, hoặc cần trích dẫn nguồn. Fine-tuning phù hợp hơn để thay đổi hành vi, định dạng hay văn phong; nó kém linh hoạt để cập nhật kiến thức thường xuyên và khó truy ngược nguồn.

**Ingestion và chunking.** Tài liệu được làm sạch rồi chia thành các đoạn (chunk) theo kích thước cố định có overlap, hoặc theo cấu trúc tài liệu (tiêu đề, mục, đoạn văn). Chunk quá nhỏ làm mất ngữ cảnh; chunk quá lớn làm loãng embedding, tốn context và chi phí. Mỗi chunk nên kèm metadata (nguồn, mục, ngày hiệu lực) để lọc và trích dẫn.

**Embedding và index.** Mô hình embedding ánh xạ văn bản thành vector; truy vấn và tài liệu phải được mã hóa bằng cùng một mô hình (hoặc cặp encoder được huấn luyện cùng nhau). Thư viện/vector database (FAISS, Qdrant, pgvector…) dùng chỉ mục tìm kiếm gần đúng (ANN) như HNSW hoặc IVF, đánh đổi một phần recall lấy tốc độ. Đổi mô hình embedding thì phải tạo lại toàn bộ index.

**Dense, sparse và hybrid.** Dense retrieval bắt được ngữ nghĩa và cách diễn đạt khác nhau. Sparse retrieval (BM25) mạnh với từ khóa chính xác: mã lỗi, tên riêng, thuật ngữ hiếm. Hybrid kết hợp hai danh sách kết quả, thường bằng Reciprocal Rank Fusion (RRF — cộng nghịch đảo thứ hạng) hoặc chuẩn hóa điểm rồi cộng có trọng số, vì điểm thô của hai bên không cùng thang đo. Hybrid không mặc nhiên tốt hơn; phải đo trên bộ truy vấn của chính hệ thống.

**Reranking.** Cross-encoder reranker đọc đồng thời truy vấn và từng đoạn để chấm lại top-N kết quả. Nó chính xác hơn bi-encoder dùng cho retrieval nhưng chậm hơn nhiều, nên chỉ áp dụng cho N nhỏ (vài chục đoạn). Đổi lại độ chính xác ở top-K là latency và chi phí tăng.

**Generation.** Prompt cần yêu cầu trả lời dựa trên ngữ cảnh được cung cấp, nói rõ khi ngữ cảnh không đủ thông tin, và trích dẫn nguồn. Đưa quá nhiều đoạn vào prompt có thể làm giảm chất lượng (thông tin nhiễu, mô hình bỏ sót thông tin nằm giữa ngữ cảnh dài) và tăng chi phí.

**Đánh giá.** Tách hai tầng. Retrieval: Recall@K, Precision@K, MRR, nDCG trên bộ truy vấn có nhãn đoạn liên quan. Generation: faithfulness/groundedness (câu trả lời có được ngữ cảnh hỗ trợ không) và độ đúng/độ liên quan của câu trả lời. Retrieval tốt chưa bảo đảm câu trả lời đúng, và ngược lại. LLM-as-judge tiện cho đánh giá quy mô lớn nhưng cần đối chiếu với nhãn của người trên một mẫu.

**Lỗi thường gặp khi vận hành.** Không truy xuất được đoạn đúng (chunking, embedding hoặc truy vấn không khớp); truy xuất đúng nhưng mô hình bỏ qua hoặc bịa thêm; index không được cập nhật khi tài liệu thay đổi; lộ tài liệu khi không lọc theo quyền của người dùng; prompt injection nằm trong nội dung tài liệu.

## Level Guidance

### Intern

- Giải thích được RAG là gì, vì sao cần và các bước chính của pipeline.
- Hiểu embedding và tìm kiếm tương đồng (cosine similarity) ở mức khái niệm; phân biệt được với tìm theo từ khóa.
- Không kỳ vọng: cách gộp kết quả hybrid, reranking, đánh giá định lượng.

### Fresher

- Thiết kế được pipeline RAG cho một bộ tài liệu cụ thể: cách chunking, chọn embedding, top-K.
- Biết hybrid retrieval, reranking và lý do dùng; biết Recall@K/MRR và tách đánh giá retrieval với generation.
- Kỳ vọng có ví dụ từ đồ án hoặc dự án cá nhân, kể cả quy mô nhỏ.

### Junior

- Phân tích lỗi có hệ thống và đề xuất thí nghiệm để chứng minh một cải tiến.
- Cân bằng chất lượng – latency – chi phí; caching, cập nhật index, phân quyền tài liệu.
- Giám sát khi chạy thật: log truy vấn, tỷ lệ "không tìm thấy thông tin", phản hồi người dùng.

## Question Seeds

### rag_basics_01 — RAG là gì, và vì sao không chỉ hỏi thẳng LLM?
**Levels:** intern, fresher
**Objective:** Hiểu mục đích của RAG và các thành phần chính của pipeline.
**Expected points:**
- LLM chỉ có tri thức đến thời điểm huấn luyện và không biết dữ liệu riêng/nội bộ.
- RAG truy xuất các đoạn tài liệu liên quan và đưa vào prompt để mô hình trả lời dựa trên đó.
- Các bước chính: chia đoạn, tạo embedding, lưu index, truy xuất top-K, sinh câu trả lời.
- Lợi ích: giảm bịa đặt, cập nhật tri thức không cần huấn luyện lại, có thể trích dẫn nguồn.
**Follow-up probes:**
- Embedding là gì và vì sao giúp tìm được đoạn văn liên quan?
- Nếu các đoạn truy xuất được không chứa câu trả lời thì mô hình nên làm gì?

### rag_search_01 — Tìm kiếm theo từ khóa và tìm kiếm theo embedding khác nhau thế nào?
**Levels:** intern, fresher
**Objective:** Phân biệt sparse retrieval và dense retrieval.
**Expected points:**
- Tìm theo từ khóa (BM25, TF-IDF) khớp từ ngữ xuất hiện trong văn bản; mạnh với tên riêng, mã, thuật ngữ chính xác.
- Tìm theo embedding so sánh vector ngữ nghĩa (ví dụ cosine similarity); tìm được đoạn diễn đạt khác nhưng cùng ý.
- Embedding có thể bỏ sót từ khóa hiếm hoặc mã lỗi; tìm theo từ khóa bỏ sót từ đồng nghĩa và cách diễn đạt khác.
- Có thể kết hợp hai cách (hybrid retrieval).
**Follow-up probes:**
- Cho một ví dụ truy vấn mà tìm theo từ khóa cho kết quả tốt hơn embedding.
- Vì sao truy vấn và tài liệu phải dùng cùng một mô hình embedding?

### rag_chunking_01 — Bạn sẽ chia đoạn (chunking) tài liệu thế nào cho một chatbot hỏi đáp nội quy công ty?
**Levels:** fresher, junior
**Objective:** Hiểu tác động của chunking lên chất lượng retrieval và chọn cấu hình bằng thí nghiệm.
**Expected points:**
- Chunk quá nhỏ mất ngữ cảnh; chunk quá lớn làm loãng embedding, tốn context và chi phí.
- Chia theo cấu trúc tài liệu (tiêu đề, mục, đoạn) thường tốt hơn cắt cứng theo số ký tự; dùng overlap để không cắt đứt ý.
- Lưu metadata (tên tài liệu, mục, ngày hiệu lực) để lọc và trích dẫn nguồn.
- Chọn kích thước bằng thí nghiệm trên bộ câu hỏi mẫu (ví dụ đo Recall@K), không chọn cảm tính.
**Follow-up probes:**
- Bạn đo thế nào để biết cách chunking mới tốt hơn cách cũ?
- Bảng biểu hoặc danh sách dài trong tài liệu thì bạn xử lý ra sao?

### rag_hybrid_01 — Khi nào nên dùng hybrid retrieval, và bạn kết hợp kết quả của hai bên thế nào?
**Levels:** fresher, junior
**Objective:** Hiểu trade-off dense/sparse/hybrid và cách chứng minh một cải tiến bằng dữ liệu.
**Expected points:**
- Dense mạnh về ngữ nghĩa; sparse (BM25) mạnh với từ khóa chính xác, tên riêng, mã; hybrid bù điểm yếu cho nhau.
- Kết hợp bằng Reciprocal Rank Fusion hoặc chuẩn hóa điểm rồi cộng có trọng số, vì điểm thô hai bên không cùng thang đo.
- Có thể thêm cross-encoder reranker cho top-N để tăng độ chính xác, đổi lại latency.
- Chứng minh bằng thí nghiệm trên bộ truy vấn có nhãn: so Recall@K/MRR với baseline chỉ dùng dense.
**Follow-up probes:**
- Vì sao không nên cộng trực tiếp điểm cosine và điểm BM25?
- Reranker làm tăng latency bao nhiêu thì chấp nhận được, và bạn quyết định dựa trên gì?

### rag_debug_01 — Chatbot RAG của bạn trả lời sai một câu hỏi; bạn tìm nguyên nhân thế nào?
**Levels:** fresher, junior
**Objective:** Phân tích lỗi theo từng tầng và đánh giá tách biệt retrieval với generation.
**Expected points:**
- Kiểm tra tầng retrieval trước: đoạn chứa câu trả lời có nằm trong top-K không (đo Recall@K trên bộ câu hỏi mẫu).
- Nếu retrieval đúng mà câu trả lời vẫn sai: xem prompt, độ dài ngữ cảnh, mô hình bỏ qua ngữ cảnh hoặc bịa thêm (faithfulness).
- Nếu retrieval sai: xem lại chunking, embedding, cách viết truy vấn, hybrid/rerank, hoặc index chưa được cập nhật.
- Xây bộ đánh giá có nhãn để đo trước và sau mỗi thay đổi; nếu dùng LLM-as-judge thì đối chiếu với nhãn người trên một mẫu.
**Follow-up probes:**
- Khi chưa có dữ liệu người dùng, bạn xây bộ câu hỏi đánh giá đầu tiên như thế nào?
- Faithfulness khác độ đúng của câu trả lời ở điểm nào?

### rag_production_01 — Khi đưa hệ thống RAG vào sử dụng thật, bạn theo dõi chất lượng và tối ưu latency, chi phí ra sao?
**Levels:** junior
**Objective:** Vận hành RAG: đo theo từng bước, tối ưu có căn cứ và giám sát chất lượng.
**Expected points:**
- Đo latency theo từng bước (embedding truy vấn, retrieval, rerank, LLM) để tìm nút thắt trước khi tối ưu.
- Giảm chi phí/latency: bớt số đoạn đưa vào prompt, cache truy vấn lặp lại, dùng mô hình nhỏ hơn cho bước phù hợp, giới hạn reranker ở top-N nhỏ.
- Theo dõi chất lượng: tỷ lệ "không tìm thấy thông tin", phản hồi người dùng, review định kỳ một mẫu log.
- Cập nhật index khi tài liệu thay đổi và lọc tài liệu theo quyền truy cập của người dùng.
**Follow-up probes:**
- Nếu cache trả về câu trả lời cũ sau khi tài liệu đã được cập nhật thì bạn xử lý thế nào?
- Bạn đặt ngưỡng cảnh báo nào cho chất lượng, và dựa trên dữ liệu gì?

## Scoring Rubric

- technical_accuracy: 0.40 — Phân biệt đúng các thành phần, loại retrieval và metric; không nhầm metric retrieval với chất lượng câu trả lời.
- completeness: 0.25 — Đối chiếu với expected points của từng câu.
- reasoning: 0.20 — Nêu trade-off chất lượng, latency, chi phí và cách chứng minh bằng thí nghiệm.
- practical_examples: 0.15 — Ví dụ từ đồ án hoặc dự án RAG đã làm, kể cả quy mô nhỏ.

## Positive Signals

- Đề xuất đo bằng bộ truy vấn có nhãn trước khi khẳng định một thay đổi là cải tiến.
- Tách bạch lỗi do retrieval và lỗi do generation.
- Nêu trade-off cụ thể khi thêm hybrid retrieval hoặc reranker.
- Nhắc tới metadata, cập nhật index và phân quyền tài liệu khi nói về hệ thống thật.

## Pitfalls

- Cho rằng hybrid hoặc reranking luôn tốt hơn mà không có dữ liệu hay metric.
- Cộng trực tiếp điểm BM25 với cosine similarity.
- Đánh giá RAG chỉ bằng vài câu hỏi thử thủ công.
- Cho rằng tăng top-K hoặc đưa thêm nhiều ngữ cảnh luôn làm câu trả lời tốt hơn.
- Đồng nhất RAG với việc "dùng vector database".

## References

- Lewis et al. (2020), Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks — https://arxiv.org/abs/2005.11401
- Cormack, Clarke & Büttcher (2009), Reciprocal Rank Fusion outperforms Condorcet and individual rank learning methods — https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf
- Liu et al. (2023), Lost in the Middle: How Language Models Use Long Contexts — https://arxiv.org/abs/2307.03172
- Es et al. (2023), RAGAS: Automated Evaluation of Retrieval Augmented Generation — https://arxiv.org/abs/2309.15217
- Qdrant documentation, Hybrid Queries — https://qdrant.tech/documentation/concepts/hybrid-queries/
- Manning, Raghavan & Schütze, Introduction to Information Retrieval (ch. 8, Evaluation) — https://nlp.stanford.edu/IR-book/

## Changelog

- 1.0.0 (2026-11-03): Bản nháp đầu tiên, chờ review.
