# SE373 · ĐỒ ÁN CUỐI KỲ: HƯỚNG DẪN & QUY ĐỊNH CHUNG

> **Môn học:** SE373 - Kỹ thuật xây dựng hệ thống Agentic AI  
> **Khoa:** Công nghệ Phần mềm - Trường Đại học Công nghệ Thông tin (ĐHQG-HCM)  
> **Trọng số điểm:** 50% tổng điểm môn học (thang điểm 10)

---

## 1. Lộ trình thực hiện đồ án (3 Phase)

Đồ án được triển khai qua 3 giai đoạn (Phase), mỗi giai đoạn gắn với khối lượng kiến thức và mốc thời gian cụ thể:

| Phase | Tên giai đoạn | Thời gian & Hạn chót | Kiến thức áp dụng | Mục tiêu & Yêu cầu kỹ thuật cần đạt |
| :--- | :--- | :--- | :--- | :--- |
| **PHASE 1** | **Bootstrap dự án** | 07/10 – 27/10 *(3 tuần, hạn cuối tuần 7)* | Buổi 1 – 5 | • Đăng ký nhóm 5 sinh viên, đề tài, danh sách use case và phân công người sở hữu.<br>• Khởi tạo repository Git, cấu hình CI/CD, phân tách codebase ứng dụng và codebase agent.<br>• Xây dựng **Agent Loop** với **≥ 2 tools**, **1 reusable skill**, có **logging từng bước (step logs)**.<br>• Hoàn thành **1 use case chạy được end-to-end** từ ứng dụng đến agent, kèm **≥ 10 evaluation cases**. |
| **PHASE 2** | **Mở rộng năng lực** | 28/10 – 10/11 *(2 tuần, hạn cuối tuần 9)* | Buổi 6 – 8 | • Tích hợp **RAG (Retrieval-Augmented Generation)** có trích dẫn nguồn (citation).<br>• Quản lý **State & Memory**: Lưu state, hỗ trợ dừng rồi chạy tiếp (checkpoint/resume), nén context.<br>• Xây dựng **Workflow điều phối (LangGraph)**, có bước người duyệt (**Human-in-the-loop / Human Approval**).<br>• Hoàn thành **≥ 3 use case chạy được**. |
| **PHASE 3** | **Hoàn thiện và nộp** | 11/11 – 06/12 *(3 tuần, hạn cuối tuần 12)* | Buổi 9 – 11 | • Xây dựng **Tập Eval đầy đủ**, chạy benchmark lại để đối sánh hiệu năng/độ chính xác.<br>• Triển khai kiến trúc **Multi-agent** hoặc tích hợp giao thức **MCP (Model Context Protocol)**.<br>• Kiểm thử an toàn (**Security & Guardrails**), trực quan hóa và truy vết (**Trace & Observability**).<br>• Hoàn thành **≥ 5 use case phủ đủ 8 mảng kiến thức (K1–K8)**; hoàn thiện báo cáo và video demo. |

> **Lưu ý quan trọng cuối mỗi Phase:**  
> - Gắn Git tag tương ứng trên repository.  
> - Nộp kèm video demo ngắn chứng minh tính năng hoạt động thực tế.  
> - Mỗi phase chỉ sử dụng kiến thức đã học đến thời điểm đó.

---

## 2. Cơ cấu và Tiêu chí tính điểm

Đồ án chiếm **50% điểm tổng kết**, chấm theo thang điểm 10 với 2 cấu phần chính:

```
Tổng điểm đồ án (10.0) = Điểm Agent (7.5) + Điểm Phần mềm (2.5)
```

### 2.1. Phần Agent (Tối đa 7.5 điểm)
- Yêu cầu tối thiểu **5 use case**, mỗi use case trị giá **1.5 điểm** (5 × 1.5 = 7.5 điểm). Có thể làm thêm use case để bù điểm nếu có use case chưa đạt trọn vẹn.
- Mỗi use case được đánh giá theo 3 tiêu chí:
  1. **Chức năng (0.5 điểm):** Chạy đúng tiêu chí nghiệp vụ đề ra.
  2. **Thiết kế Harness (0.5 điểm):** Đúng kỹ thuật kiến trúc harness (tools, skill, state, verification, loop control).
  3. **Kiểm chứng (0.5 điểm):** Có bộ eval test cases, đo lường được kết quả và hiển thị trace rõ ràng.
- **Yêu cầu phủ 8 mảng kiến thức (K1–K8):** Danh sách use case nộp phải bao quát toàn diện K1–K8. **Thiếu mỗi mảng kiến thức bị trừ 0.5 điểm**.

### 2.2. Phần Mềm (Tối đa 2.5 điểm)
- Có thể xây dựng dưới dạng **Web Application, Desktop App hoặc CLI**, nhưng **bắt buộc phải tích hợp agent thật**.
- Tiêu chí đánh giá:
  - **Sáng tạo:** 0.5 điểm
  - **Độ phức tạp kỹ thuật:** 0.75 điểm
  - **Độ hoàn thiện (UI/UX, độ ổn định):** 0.75 điểm
  - **Khối lượng công việc:** 0.5 điểm

### 2.3. Đánh giá cá nhân và Quy định vi phạm
- **Điểm cá nhân:** = Điểm nhóm × Hệ số vấn đáp (0.0 – 1.0) của từng thành viên. Mỗi thành viên phải trình bày được use case mình sở hữu và trả lời câu hỏi về thiết kế agent.
- **Quy định trừ điểm / kỷ luật:**
  - Lộ API key trên repository/commit: **Trừ 1.0 điểm**.
  - Sao chép, gian lận: **0 điểm đồ án**.

---

## 3. Trình bày và Bảo vệ đồ án

- **Buổi 1 - Trình bày trong nhóm nhỏ (Pool):**
  - 1 pool gồm 10 nhóm, do 1 Giảng viên Thực hành (GVTH) phụ trách hướng dẫn và chấm điểm.
  - Mỗi nhóm demo và bảo vệ use case của mình.
  - Mỗi pool chọn ra **2 đề tài xuất sắc nhất** vào vòng chung khảo.
- **Buổi 2 - Trình bày trước cả lớp:**
  - 10 đề tài xuất sắc nhất từ các pool trình bày và demo trước toàn thể giảng viên và sinh viên lớp.

---

## 4. Chi tiết Đề tài số 2: Code Review Agent

- **Tên đề tài:** Code Review Agent
- **Giảng viên Thực hành phụ trách:** ThS. Nguyễn Ngọc Quí (NNQuí)
- **Mô tả cốt lõi:**
  > *Comment trực tiếp lên Pull Request kèm mức độ (severity) và gợi ý sửa code (code fix suggestion); nhiều reviewer chuyên biệt; học từ phản hồi của team.*

### Phân tích kiến trúc & Tính năng cốt lõi cho Đề tài số 2:
1. **Tương tác PR trực tiếp (GitHub/GitLab Integration):**
   - Đọc PR diff, commit changes, file AST, context xung quanh code thay đổi.
   - Viết inline comments chính xác vào đúng dòng thay đổi (`path`, `line`, `side`).
   - Cung cấp gợi ý sửa trực tiếp bằng cú pháp ` ```suggestion ` để dev có thể apply 1-click.
2. **Hệ thống phân cấp mức độ (Severity Classification):**
   - Phân loại rõ ràng: `CRITICAL` / `BLOCKER`, `HIGH`, `MEDIUM`, `LOW` / `NITPICK`, `INFO`.
   - Phân loại danh mục: Security, Performance, Logic/Bug, Style/Convention, Test/Doc.
3. **Kiến trúc Multi-Reviewer Chuyên biệt:**
   - **Security Reviewer:** Chuyên quét lỗ hổng SQLi, XSS, SSRF, Auth/Authz, credential leaks.
   - **Performance Reviewer:** Chuyên phát hiện time/space complexity, N+1 query, resource leaks, unindexed queries.
   - **Bug & Logic Reviewer:** Chuyên phân tích edge cases, null pointer, race conditions, type mismatch.
   - **Style & Clean Code Reviewer:** Chuyên kiểm tra code conventions, design patterns (SOLID), DRY.
4. **Học từ phản hồi của Team (Feedback Learning Loop):**
   - Lưu trữ các phản hồi của team (thích/không thích review, dev reject hay accept gợi ý).
   - Lưu conventions và coding guidelines riêng của repo vào Vector DB / Memory Store.
   - Nâng cao độ chính xác theo thời gian, giảm thiểu false-positive review.
