---
id: programming_fundamentals
kind: competency_skill
version: 1.0.0
assessment: question
levels: [intern, fresher, junior]
keywords: [python, java, javascript, typescript, go, c++, oop, data structures, algorithms, big-o, unit test, pytest, git, async, debugging]
status: draft
---

# Programming Fundamentals

## Learning Objectives

- Chọn cấu trúc dữ liệu phù hợp và phân tích độ phức tạp thuật toán.
- Áp dụng nguyên lý hướng đối tượng hợp lý.
- Debug có phương pháp, viết kiểm thử và hiểu mô hình xử lý đồng thời.

## Core Knowledge

- List/array truy cập theo chỉ số O(1) nhưng tìm kiếm theo giá trị O(n); dict/hash map và set tra cứu trung bình O(1). Chọn cấu trúc theo thao tác chiếm ưu thế.
- Big-O mô tả tốc độ tăng chi phí theo kích thước đầu vào; hai vòng lặp lồng nhau trên n phần tử thường là O(n²), có thể giảm bằng hash set hoặc sắp xếp.
- Class là bản thiết kế, object là thể hiện. Kế thừa thể hiện quan hệ "là một"; composition (chứa đối tượng khác) thường linh hoạt và ít ràng buộc hơn.
- Debug có phương pháp: tái hiện lỗi với case nhỏ nhất, kiểm tra input/output từng lớp, đọc log, đặt giả thuyết rồi kiểm chứng; sau khi sửa thì thêm test để chống tái phát.
- Unit test kiểm tra từng đơn vị độc lập với trường hợp bình thường, biên và lỗi; mock phụ thuộc bên ngoài.
- async/await phù hợp tác vụ chờ I/O (mạng, database) trên một luồng; tác vụ nặng CPU trong hàm async sẽ chặn event loop, nên chuyển sang process/thread riêng.
- Tối ưu hiệu năng phải bắt đầu bằng đo (profiling), không đoán.

## Level Guidance

### Intern

- Cấu trúc dữ liệu cơ bản, độ phức tạp đơn giản, OOP cơ bản, debug có trình tự.

### Fresher

- Viết unit test có trường hợp biên, hiểu async và đa luồng, lập kế hoạch debug.

### Junior

- Profile và tối ưu hiệu năng có kiểm chứng, đánh giá trade-off về khả năng bảo trì.

## Question Seeds

### pf_01 — List và dict trong Python khác nhau thế nào? Khi nào dùng cái nào, và độ phức tạp khi tìm kiếm ra sao?
**Levels:** intern, fresher
**Objective:** Chọn cấu trúc dữ liệu theo thao tác và hiểu độ phức tạp.
**Expected points:**
- List là dãy có thứ tự, truy cập theo chỉ số; dict lưu cặp khóa–giá trị.
- Tìm theo giá trị trong list là O(n); tra cứu theo khóa trong dict trung bình O(1) nhờ hash.
- Dùng dict/set khi cần tra cứu nhanh theo khóa hoặc kiểm tra tồn tại.
**Follow-up probes:**
- Set khác dict ở điểm nào?
- Vì sao khóa của dict phải là kiểu bất biến (hashable)?
**Scoring caution:** Không yêu cầu nhớ chi tiết cài đặt bên trong; chấm cách chọn cấu trúc.

### pf_02 — Một hàm dùng hai vòng lặp lồng nhau để tìm phần tử trùng trong danh sách. Độ phức tạp là bao nhiêu và cải thiện thế nào?
**Levels:** intern, fresher
**Objective:** Phân tích Big-O và giảm độ phức tạp bằng cấu trúc dữ liệu phù hợp.
**Expected points:**
- Hai vòng lặp lồng nhau trên n phần tử là O(n²).
- Dùng set để đánh dấu phần tử đã gặp, giảm còn O(n) thời gian, đổi lại O(n) bộ nhớ.
- Hoặc sắp xếp rồi so sánh phần tử kề nhau với O(n log n).
**Follow-up probes:**
- Đánh đổi thời gian và bộ nhớ ở đây là gì?
- Nếu danh sách quá lớn để nằm trong bộ nhớ thì sao?
**Scoring caution:** Chấp nhận nhiều cách cải thiện hợp lệ nếu phân tích đúng độ phức tạp.

### pf_03 — Phân biệt class và object. Khi nào nên dùng kế thừa, khi nào nên dùng composition?
**Levels:** intern, fresher
**Objective:** Hiểu OOP cơ bản và lựa chọn thiết kế.
**Expected points:**
- Class là bản thiết kế; object là thể hiện cụ thể với dữ liệu riêng.
- Kế thừa dùng khi có quan hệ "là một" và muốn tái sử dụng hành vi chung.
- Composition (chứa đối tượng khác) linh hoạt hơn, ít ràng buộc; thường được ưu tiên khi quan hệ là "có một".
**Follow-up probes:**
- Kế thừa nhiều tầng gây ra vấn đề gì?
- Cho một ví dụ từ dự án bạn đã làm.
**Scoring caution:** Không yêu cầu thuộc định nghĩa sách vở; chấm khả năng áp dụng.

### pf_04 — Một API hoặc hàm trả kết quả khác với mong đợi. Bạn bắt đầu kiểm tra từ đâu?
**Levels:** intern, fresher, junior
**Objective:** Debug có phương pháp thay vì đoán mò.
**Expected points:**
- Xác nhận lại input, output thực tế và kết quả mong đợi.
- Tái hiện lỗi với case tối giản.
- Kiểm tra log và từng lớp xử lý để khoanh vùng; sửa rồi thêm test chống tái phát.
**Follow-up probes:**
- Nếu lỗi lúc có lúc không, bạn thu thập thêm thông tin gì?
- Sau khi sửa, bạn viết test nào?
**Scoring caution:** Không coi việc đoán nguyên nhân là đã có bằng chứng.

### pf_05 — Bạn viết unit test cho một hàm tính phí giao hàng theo khoảng cách và khối lượng thế nào?
**Levels:** fresher, junior
**Objective:** Thiết kế test có trường hợp bình thường, biên và lỗi.
**Expected points:**
- Test trường hợp bình thường với kết quả đã biết.
- Test giá trị biên (0, ngưỡng chuyển bậc phí, giá trị rất lớn) và đầu vào không hợp lệ (âm, thiếu).
- Mỗi test độc lập, rõ ý định; mock phụ thuộc bên ngoài nếu có (ví dụ API bảng giá).
**Follow-up probes:**
- Khi nào cần integration test thay vì unit test?
- Độ phủ test 100% có đảm bảo không còn lỗi không?
**Scoring caution:** Không chấm cao nếu chỉ test happy path.

### pf_06 — async/await khác đa luồng thế nào? Một tác vụ nặng CPU đặt trong hàm async gây ra vấn đề gì?
**Levels:** fresher, junior
**Objective:** Hiểu mô hình xử lý đồng thời và tác động lên hiệu năng.
**Expected points:**
- async/await chạy nhiều tác vụ trên một event loop, phù hợp với chờ I/O.
- Đa luồng/đa tiến trình chạy song song thật hơn; trong Python, tác vụ CPU nặng thường cần process riêng.
- Tác vụ CPU nặng trong hàm async chặn event loop, làm mọi request khác bị chậm; nên chuyển sang thread/process pool hoặc worker.
**Follow-up probes:**
- Gọi một thư viện database đồng bộ trong hàm async thì sao?
- Bạn phát hiện event loop bị chặn bằng cách nào?
**Scoring caution:** Không chấp nhận "async luôn nhanh hơn".

### pf_07 — Một hàm xử lý chạy chậm dần khi dữ liệu tăng. Bạn tìm nguyên nhân và tối ưu thế nào?
**Levels:** junior
**Objective:** Tối ưu hiệu năng dựa trên profiling và kiểm chứng.
**Expected points:**
- Đo bằng profiler để tìm phần tốn thời gian thay vì đoán.
- Phân tích độ phức tạp, truy vấn lặp (N+1), cấp phát bộ nhớ không cần thiết.
- Tối ưu phần nóng nhất, đo lại và đảm bảo test vẫn đúng.
**Follow-up probes:**
- Khi nào nên dùng cache cho kết quả tính toán?
- Bạn tránh tối ưu sớm làm code khó bảo trì thế nào?
**Scoring caution:** Không chấp nhận tối ưu mà không có số đo trước và sau.

## Scoring Rubric

- technical_accuracy: 0.40 — Kiến thức cấu trúc dữ liệu, độ phức tạp, OOP và đồng thời đúng.
- completeness: 0.25 — Đối chiếu expected points của từng câu.
- reasoning: 0.20 — Lập luận về trade-off và cách kiểm chứng (test, profiling).
- practical_examples: 0.15 — Ví dụ từ bài tập, đồ án hoặc dự án đã làm.

## Positive Signals

- Chọn cấu trúc dữ liệu dựa trên thao tác chính và nói được độ phức tạp.
- Debug có trình tự, tái hiện lỗi trước khi sửa và thêm test sau khi sửa.
- Đo trước khi tối ưu.

## Pitfalls

- Học thuộc định nghĩa nhưng không áp dụng được vào ví dụ.
- Chỉ kiểm thử happy path.
- Tối ưu theo cảm tính, không đo.

## References

- Python documentation, Data Structures — https://docs.python.org/3/tutorial/datastructures.html
- Python Wiki, Time Complexity — https://wiki.python.org/moin/TimeComplexity
- Python documentation, asyncio — https://docs.python.org/3/library/asyncio.html
- pytest documentation — https://docs.pytest.org/

## Changelog

- 1.0.0 (2026-11-03): Bản nháp đầu tiên (bổ sung so với IntervAI Skill Library v1.0), gộp câu debug từ problem_solving; chờ review.
