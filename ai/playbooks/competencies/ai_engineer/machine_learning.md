---
id: machine_learning
kind: competency_skill
version: 1.0.0
assessment: question
levels: [intern, fresher, junior]
keywords: [machine learning, scikit-learn, sklearn, classification, regression, overfitting, cross-validation, xgboost, lightgbm, feature engineering, supervised learning]
status: draft
---

# Machine Learning Foundations

## Learning Objectives

- Hiểu train/validation/test, generalization và cách tránh rò rỉ dữ liệu (data leakage).
- Chọn metric phù hợp mục tiêu, đặc biệt khi dữ liệu mất cân bằng.
- Dựng baseline, phân tích lỗi và nhận diện distribution shift.

## Core Knowledge

- Supervised learning cần nhãn và tập dữ liệu đại diện cho lúc sử dụng thật; rò rỉ dữ liệu giữa train và test làm kết quả đánh giá ảo.
- Train dùng để fit mô hình, validation để chọn mô hình/siêu tham số, test giữ riêng đến cuối để ước lượng khả năng tổng quát hóa. Cross-validation và tuning chỉ chạy trên train/validation.
- Overfitting: mô hình học cả nhiễu của dữ liệu huấn luyện, điểm train cao nhưng validation kém. Xử lý bằng regularization, giảm độ phức tạp, thêm/đa dạng hóa dữ liệu, early stopping — không phải tăng epoch.
- Precision, recall, F1, PR curve phù hợp cho phân loại (nhất là khi mất cân bằng lớp); MAE, RMSE, R² cho hồi quy. Với lớp hiếm, accuracy dễ gây hiểu lầm; cần confusion matrix và metric theo lớp. Ngưỡng phân loại chọn theo chi phí của false positive và false negative.
- Khi dữ liệu thay đổi theo thời gian hoặc theo người dùng, cần chia tập theo thời gian/nhóm thay vì chia ngẫu nhiên, và theo dõi drift sau triển khai.

## Level Guidance

### Intern

- Nắm học có giám sát, overfitting và vai trò của từng tập dữ liệu.
- Biết vì sao accuracy không đủ khi lớp mất cân bằng.

### Fresher

- Chọn metric đúng mục tiêu, thiết kế baseline và quy trình validation đáng tin.
- Phân tích được vì sao kết quả test cao nhưng dùng thật lại kém.

### Junior

- Phát hiện leakage tinh vi và distribution shift; thiết kế đánh giá theo thời gian và theo phân khúc.
- Đề xuất điều kiện huấn luyện lại và giám sát sau triển khai.

## Question Seeds

### ml_01 — Tại sao phải chia dữ liệu thành train, validation và test?
**Levels:** intern, fresher
**Objective:** Hiểu vai trò của từng tập và cách ước lượng khả năng tổng quát hóa.
**Expected points:**
- Train dùng để fit tham số mô hình.
- Validation dùng để chọn mô hình hoặc siêu tham số.
- Test giữ độc lập đến cuối để ước lượng hiệu năng trên dữ liệu mới.
**Follow-up probes:**
- Nếu tune mô hình trên tập test nhiều lần thì chuyện gì xảy ra?
- Khi dữ liệu ít, bạn có thể dùng cách nào khác (ví dụ k-fold)?
**Scoring caution:** Không chấp nhận việc dùng tập test để huấn luyện hoặc chọn siêu tham số.

### ml_02 — Overfitting là gì, và bạn phát hiện, xử lý nó thế nào?
**Levels:** intern, fresher
**Objective:** Nhận diện overfitting qua learning curve và biết các biện pháp giảm.
**Expected points:**
- Mô hình học thuộc dữ liệu huấn luyện kể cả nhiễu: điểm train cao nhưng validation kém.
- Phát hiện bằng so sánh loss/metric giữa train và validation theo thời gian huấn luyện.
- Xử lý: regularization, giảm độ phức tạp, thêm hoặc đa dạng hóa dữ liệu, early stopping.
**Follow-up probes:**
- Nếu dữ liệu chỉ có vài trăm mẫu, bạn chia tập đánh giá thế nào cho đáng tin?
- Underfitting khác overfitting ở dấu hiệu nào?
**Scoring caution:** Không coi "train thêm epoch" là cách chữa overfitting.

### ml_03 — Bộ phân loại gian lận có 1% mẫu dương tính và đạt accuracy 99%. Điều đó có đủ tốt không?
**Levels:** intern, fresher
**Objective:** Hiểu hạn chế của accuracy khi mất cân bằng lớp và chọn metric theo chi phí lỗi.
**Expected points:**
- Không đủ: một mô hình đoán toàn bộ là âm tính cũng đạt 99% accuracy.
- Cần xem recall, precision, PR curve và confusion matrix.
- Chọn ngưỡng theo chi phí của false positive và false negative.
**Follow-up probes:**
- Nếu bỏ sót gian lận đắt hơn báo nhầm thì bạn ưu tiên metric nào?
- Bạn so sánh mô hình với baseline nào?
**Scoring caution:** Không giả định có một ngưỡng tối ưu chung cho mọi bài toán.

### ml_04 — Điểm test rất cao nhưng khi demo với dữ liệu thật thì mô hình lại kém. Bạn kiểm tra gì?
**Levels:** fresher, junior
**Objective:** Chẩn đoán leakage và lệch phân phối giữa dữ liệu đánh giá và dữ liệu thật.
**Expected points:**
- Rà soát data leakage và cách chia tập (trùng mẫu, đặc trưng chứa thông tin tương lai).
- So sánh phân phối train/test với dữ liệu thật (distribution shift).
- Kiểm tra tiền xử lý không đồng nhất giữa lúc train và lúc dùng, cùng chất lượng nhãn.
**Follow-up probes:**
- Chia theo thời gian hoặc theo người dùng khác gì chia ngẫu nhiên?
- Bạn thiết kế phân tích theo nhóm dữ liệu (slice analysis) thế nào?
**Scoring caution:** Không kết luận "mô hình yếu" khi chưa kiểm chứng dữ liệu và pipeline.

### ml_05 — Thiết kế quy trình đánh giá mô hình dự đoán giá xe khi dữ liệu thay đổi theo từng năm.
**Levels:** junior
**Objective:** Đánh giá có xét yếu tố thời gian, theo phân khúc và kế hoạch giám sát drift.
**Expected points:**
- Chia tập theo thời gian (train trên quá khứ, đánh giá trên giai đoạn sau) và giữ holdout.
- So sánh MAE/RMSE theo phân khúc và theo năm, không chỉ con số trung bình.
- Theo dõi drift sau triển khai và đặt điều kiện huấn luyện lại.
**Follow-up probes:**
- Bạn xử lý outlier thế nào để không gây leakage?
- Nếu R² tốt nhưng sai số lớn ở dòng xe hiếm thì sao?
**Scoring caution:** Có nhiều giải pháp hợp lệ; chấm theo lập luận, không theo một đáp án duy nhất.

## Scoring Rubric

- technical_accuracy: 0.40 — Khái niệm về tập dữ liệu, overfitting và metric đúng; không nhầm vai trò validation và test.
- completeness: 0.25 — Đối chiếu expected points của từng câu.
- reasoning: 0.25 — Thiết kế đánh giá đáng tin: baseline, chống leakage, phân tích theo slice, chi phí FP/FN.
- practical_examples: 0.10 — Ví dụ từ đồ án hoặc dự án, kể cả quy mô nhỏ.

## Positive Signals

- Nhắc tới baseline, leakage và metric theo mục tiêu trước khi nói tới mô hình.
- Phân tích rõ false positive, false negative và vai trò của từng tập dữ liệu.
- Phân tích lỗi theo nhóm dữ liệu thay vì chỉ nhìn một con số tổng.

## Pitfalls

- Chỉ báo accuracy mà không nói tới mất cân bằng lớp.
- Tune trên tập test rồi coi kết quả là độc lập.
- Chia ngẫu nhiên khi dữ liệu có yếu tố thời gian.

## References

- scikit-learn, Model evaluation — https://scikit-learn.org/stable/modules/model_evaluation.html
- scikit-learn, Cross-validation — https://scikit-learn.org/stable/modules/cross_validation.html
- Google Machine Learning Crash Course — https://developers.google.com/machine-learning/crash-course

## Changelog

- 1.0.0 (2026-11-03): Chuyển đổi từ IntervAI Skill Library v1.0, thêm câu overfitting; chờ review.
