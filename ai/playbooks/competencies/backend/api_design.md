---
id: api_design
kind: competency_skill
version: 1.0.0
assessment: question
levels: [intern, fresher, junior]
keywords: [rest, restful, api, http, fastapi, django, flask, express, spring boot, openapi, graphql, grpc, jwt, oauth, idempotency]
status: draft
---

# API Design & Backend Reliability

## Learning Objectives

- Thiết kế REST API dễ dùng: tài nguyên, method, status code, validation và contract rõ ràng.
- Đảm bảo bảo mật (xác thực, phân quyền), idempotency và khả năng quan sát.
- Thay đổi API mà không phá vỡ client cũ.

## Core Knowledge

- GET đọc dữ liệu; POST tạo mới hoặc thực hiện thao tác; PUT thay thế tài nguyên; PATCH cập nhật một phần; DELETE xóa. GET, PUT, DELETE là idempotent theo ngữ nghĩa HTTP; POST thì không.
- Status code: 400 request sai, 401 chưa xác thực, 403 không đủ quyền, 404 không tìm thấy, 409 xung đột trạng thái, 422 dữ liệu không hợp lệ (phổ biến với FastAPI), 5xx lỗi phía server.
- Phân trang, lọc, sắp xếp phải rõ ràng, có giới hạn và ổn định; offset đơn giản nhưng chậm và lệch khi dữ liệu thay đổi, cursor ổn định hơn nhưng không nhảy trang tùy ý.
- Idempotency key giúp client retry an toàn khi tạo/ghi dữ liệu; phân biệt lỗi retry được và không.
- Validation đầu vào không thay thế phân quyền; server phải kiểm tra quyền trên từng tài nguyên.
- Thay đổi contract cần chiến lược phiên bản và deprecation; không xóa hay đổi nghĩa field đột ngột.

## Level Guidance

### Intern

- Hiểu route, request/response, HTTP method và status code cơ bản.

### Fresher

- Thiết kế API CRUD có validation, phân trang, xác thực/phân quyền và kiểm thử.

### Junior

- Xử lý concurrency, idempotency, tương thích ngược, giám sát và phát hành an toàn.

## Question Seeds

### api_01 — Phân biệt GET, POST, PUT, PATCH và cho ví dụ với API quản lý đơn hàng.
**Levels:** intern, fresher
**Objective:** Hiểu ngữ nghĩa của các HTTP method và tính idempotent.
**Expected points:**
- GET để đọc; POST để tạo mới hoặc thực hiện thao tác.
- PUT thay thế tài nguyên; PATCH cập nhật một phần.
- Chọn method theo ngữ nghĩa và tính idempotent (GET, PUT idempotent; POST không).
**Follow-up probes:**
- Khi tài nguyên không tồn tại, bạn trả status code nào?
- 401 và 403 khác nhau thế nào?
**Scoring caution:** Không cứng nhắc một quy ước duy nhất cho mọi hệ thống, miễn nhất quán với contract.

### api_02 — Khi API trả lỗi, bạn chọn status code thế nào? Phân biệt 400, 401, 403, 404, 422 và 500.
**Levels:** intern, fresher
**Objective:** Dùng status code đúng ngữ nghĩa để client xử lý lỗi được.
**Expected points:**
- 400/422: request hoặc dữ liệu không hợp lệ; client cần sửa request.
- 401: chưa xác thực; 403: đã xác thực nhưng không đủ quyền.
- 404: không tìm thấy tài nguyên; 500: lỗi phía server, không phải lỗi của client.
- Body lỗi nên có cấu trúc thống nhất để client đọc được.
**Follow-up probes:**
- Khi người dùng truy cập đơn hàng của người khác, nên trả 403 hay 404, vì sao?
- Bạn có trả chi tiết lỗi nội bộ (stack trace) cho client không?
**Scoring caution:** Không chấp nhận trả 200 cho mọi trường hợp lỗi.

### api_03 — Thiết kế API lấy danh sách đơn hàng có lọc theo trạng thái và phân trang.
**Levels:** fresher, junior
**Objective:** Thiết kế endpoint danh sách an toàn, có giới hạn và kiểm thử được.
**Expected points:**
- Định nghĩa query params (trạng thái, giới hạn, con trỏ/trang) và schema response.
- Validate giới hạn kích thước trang, tham số sắp xếp và lọc.
- Chỉ trả đơn hàng người dùng có quyền xem; kiểm thử các trường hợp biên.
**Follow-up probes:**
- Nếu dữ liệu thay đổi trong khi phân trang bằng offset thì sao?
- Bạn đảm bảo người dùng chỉ đọc được đơn của mình thế nào?
**Scoring caution:** Không cho phép query tùy ý truy cập dữ liệu của người khác.

### api_04 — Client gửi lệnh tạo thanh toán, bị timeout rồi gửi lại. Bạn xử lý thế nào để không tạo hai giao dịch?
**Levels:** fresher, junior
**Objective:** Thiết kế idempotency cho thao tác ghi có tác dụng phụ.
**Expected points:**
- Dùng idempotency key gắn với một yêu cầu logic.
- Lưu kết quả xử lý trong cùng transaction với thao tác ghi.
- Khi nhận lại cùng key, trả kết quả cũ thay vì xử lý lần nữa.
**Follow-up probes:**
- Nếu hai request cùng key đến đồng thời thì sao?
- Bạn dùng correlation ID trong log thế nào?
**Scoring caution:** Không coi POST là idempotent một cách mặc định.

### api_05 — Bạn vừa đổi schema response và ứng dụng mobile phiên bản cũ bị lỗi. Bạn thiết kế tương thích ngược thế nào?
**Levels:** junior
**Objective:** Quản lý thay đổi contract API mà không phá vỡ client cũ.
**Expected points:**
- Quản lý contract và phiên bản API, có chính sách deprecation.
- Kiểm thử contract với client, không xóa hoặc đổi nghĩa field đột ngột.
- Phát hành dần, theo dõi tỷ lệ lỗi và có kế hoạch rollback.
**Follow-up probes:**
- Bạn thông báo thay đổi cho các team client thế nào?
- Khi nào thực sự cần API v2?
**Scoring caution:** Không chấp nhận breaking change âm thầm.

## Scoring Rubric

- technical_accuracy: 0.40 — Ngữ nghĩa HTTP và contract API đúng; xác thực/phân quyền đặt ở server.
- completeness: 0.25 — Đối chiếu expected points của từng câu.
- reasoning: 0.20 — Độ tin cậy: idempotency, xử lý lỗi, tương thích ngược, trade-off phân trang.
- practical_examples: 0.15 — Kiểm thử, quan sát và ví dụ từ API đã xây.

## Positive Signals

- Thiết kế API nhất quán và nêu rõ các lỗi có thể xảy ra.
- Có kiểm thử phân quyền, retry và biên phân trang.
- Nghĩ tới client cũ khi thay đổi contract.

## Pitfalls

- Dùng HTTP 200 cho mọi trạng thái mà không có contract.
- Chỉ bảo vệ ở giao diện, không kiểm tra quyền ở server.
- Lộ thông tin nội bộ trong thông báo lỗi.

## References

- FastAPI Tutorial — https://fastapi.tiangolo.com/tutorial/
- RFC 9110, HTTP Semantics — https://www.rfc-editor.org/rfc/rfc9110.html
- MDN, HTTP response status codes — https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status

## Changelog

- 1.0.0 (2026-11-03): Chuyển đổi từ IntervAI Skill Library v1.0, thêm câu status code; chờ review.
