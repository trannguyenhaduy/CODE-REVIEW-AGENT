# 📋 BẢNG THEO DÕI TIẾN ĐỘ ĐỒ ÁN SE373 · ĐỀ TÀI SỐ 2: CODE REVIEW AGENT

> **Khoa:** Công nghệ Phần mềm - UIT  
> **GVTH Phụ trách:** ThS. Nguyễn Ngọc Quí  
> **Mục tiêu:** 10.0 / 10.0 (7.5 điểm Agent + 2.5 điểm Phần mềm)  
> **Cách cập nhật tự động:** Chạy lệnh `python scripts/update_progress.py` sau khi tích `[x]` các task.

---

## 1. Bảng Điều khiển Tiến độ Tổng quan

<!-- PROGRESS_SUMMARY_START -->
### 📊 Tổng quan Tiến độ Hiện tại: **35.9%**
```text
[█████████░░░░░░░░░░░░░░░░] 35.9% (14/39 công việc hoàn thành)
```

| Giai đoạn | Đã xong / Tổng số | Tiến độ | Trạng thái |
| :--- | :---: | :---: | :--- |
| **Giai đoạn 0: Khởi tạo & Nền tảng** | 4/4 | **100.0%** | ✅ Hoàn thành |
| **Phase 1: Bootstrap dự án (Tuần 5–7)** | 10/12 | **83.3%** | 🔄 Đang thực hiện |
| **Phase 2: Mở rộng năng lực (Tuần 8–9)** | 0/10 | **0.0%** | ⏳ Chờ thực hiện |
| **Phase 3: Hoàn thiện & Nộp (Tuần 10–12)** | 0/13 | **0.0%** | ⏳ Chờ thực hiện |
| **TỔNG CỘNG TOÀN DỰ ÁN** | **14/39** | **35.9%** | **🚀 ĐANG TRIỂN KHAI** |
<!-- PROGRESS_SUMMARY_END -->

---

## 2. Chi tiết Checklist Từng Giai đoạn

### Giai đoạn 0: Khởi tạo & Chuẩn bị Nền tảng
- [x] Khảo sát đề tài và phân tích yêu cầu Đề tài số 2: Code Review Agent.
- [x] Đóng gói toàn bộ 5 tài liệu lý thuyết môn học vào thư mục `reference/`.
- [x] Xây dựng gói Skill chuẩn kiến trúc môn học tại `skills/pr-code-review/` (kèm `SKILL.md`, `references/`, `scripts/`, `examples/`).
- [x] Lập bản kế hoạch tổng thể (Master Plan) 3 Phase & phân chia 5 Use Cases phủ đủ K1–K8.

---

### Giai đoạn 1: Phase 1 - Bootstrap Dự án (Tuần 5–7: 07/10 – 27/10)
*Mục tiêu: Dựng agent loop với ≥ 2 tools, 1 skill chuẩn, có step logging, UC1 chạy end-to-end, ≥ 10 eval cases.*
- [x] Khởi tạo khung cấu trúc repo chuẩn, phân tách `agent/` (harness) và `app/` (giao diện/API).
- [x] Cấu hình file `.gitignore` chặn commit file `.env` chứa API key (vi phạm bị trừ 1.0đ).
- [x] Thiết lập GitHub Actions CI cơ bản (kiểm tra linting và pytest).
- [x] Lập trình Tool 1: `GitDiffReader` (parse git diff patch thành danh sách file và dòng thay đổi).
- [x] Lập trình Tool 2: `FileContextReader` (đọc nội dung file xung quanh vùng diff).
- [x] Cài đặt Agent ReAct Loop với Pydantic Structured Output cho `CodeIssue` & `ReviewVerdict`.
- [x] Cài đặt Step Logging: Ghi vết chi tiết từng vòng (Step, Thought, Tool Call, Observation, Token, Latency).
- [x] Xây dựng bộ ≥ 10 Eval Test Cases đầu tiên trong `eval/dataset/`.
- [x] Kết nối UC1 chạy end-to-end từ ứng dụng tới Agent (nhập PR diff $\rightarrow$ nhận inline suggestions).
- [x] Chạy benchmark Phase 1 đo lường độ chính xác và xuất báo cáo đối sánh.
- [ ] Quay video demo ngắn (3–5 phút) chứng minh agent loop chạy thật và hiển thị log từng bước.
- [ ] Gắn Git tag `phase-1-bootstrap` trên repository và nộp tiến độ tuần 7.

---

### Giai đoạn 2: Phase 2 - Mở rộng Năng lực (Tuần 8–9: 28/10 – 10/11)
*Mục tiêu: RAG có trích dẫn nguồn (UC2), State checkpoint/resume và Human-in-the-Loop duyệt comment (UC3/UC7).*
- [ ] Xây dựng pipeline RAG: Chunking & Index tài liệu Coding Conventions của repo vào Vector DB (UC2).
- [ ] Tích hợp tính năng trích dẫn nguồn (Citation: tên file, số dòng quy ước) vào review comment.
- [ ] Cài đặt kỹ thuật nén Context Window (lọc bỏ file lock/minified) khi diff quá lớn.
- [ ] Cấu hình LangGraph StateGraph quản lý State tác vụ và lưu Checkpoint vào SQLite.
- [ ] Hỗ trợ tính năng dừng và tiếp tục (Resume) khi PR có push commit mới mà không review lại từ đầu.
- [ ] Xây dựng điểm dừng Human-in-the-Loop (HITL - UC7): Cho phép developer xem, chỉnh sửa hoặc bỏ qua comment trước khi post lên GitHub.
- [ ] Xây dựng backend Web API (`app/server.py` bằng FastAPI) với endpoints `/api/review`, `/api/approval` phục vụ HITL.
- [ ] Xây dựng prototype giao diện Web duyệt finding (Approve / Reject / Edit inline suggestion) cho UC-07.
- [ ] Đảm bảo ≥ 3 use cases chạy hoàn hảo từ app tới agent.
- [ ] Quay video demo Phase 2, gắn Git tag `phase-2-expansion` và nộp tiến độ tuần 9.

---

### Giai đoạn 3: Phase 3 - Hoàn thiện & Nộp (Tuần 10–12: 11/11 – 06/12)
*Mục tiêu: Multi-agent / MCP (UC4), Adaptive Memory học từ team (UC5), Guardrails an toàn, Trace, Báo cáo & Video.*
- [ ] Xây dựng hội đồng Multi-Agent (LangGraph) với 3 reviewer: Security, Performance, Logic (UC4).
- [ ] Tích hợp giao thức MCP (Model Context Protocol) kết nối với GitHub MCP server.
- [ ] Triển khai cơ chế Adaptive Memory: Ghi nhận dev feedback (thích/không thích/ignore) để giảm False Positives (UC5).
- [ ] Kiểm thử an toàn & Security Guardrails: Chặn prompt injection ẩn trong git commit code.
- [ ] Phân quyền an toàn: Thiết lập chế độ Read-only mặc định, chặn hành vi ghi đè branch/repo.
- [ ] Gắn kết hệ thống Observability & Tracing (LangSmith / OpenTelemetry) xem toàn bộ trace đồ thị.
- [ ] Mở rộng bộ Golden Eval Dataset lên 15–20 cases và chạy benchmark đối sánh độ cải thiện qua 3 Phase.
- [ ] Hoàn thiện Web Dashboard (`app/server.py` + `app/static/` Dark Theme): Đạt 2.5đ phần mềm với 3 tab: PR Review Live, HITL Approval Gate, Trace Graph & Benchmark Dashboard.
- [ ] Tối ưu hóa CLI Runner (`app/cli.py`) phục vụ chạy batch eval và tích hợp GitHub Actions CI.
- [ ] Đảm bảo hoàn thành ≥ 5 use cases chạy hoàn hảo phủ trọn vẹn 8 mảng kiến thức K1–K8.
- [ ] Viết Báo cáo đồ án chi tiết (PDF) kèm các bảng minh chứng kiến trúc và kết quả đo lường.
- [ ] Quay Video demo chung cuộc chất lượng cao và chuẩn bị slide thuyết trình.
- [ ] Gắn Git tag `phase-3-final` và chuẩn bị bảo vệ trước hội đồng chấm thi.

---

## 3. Hướng dẫn Nhóm Cập nhật Tiến độ

Mỗi khi bạn hoặc thành viên trong nhóm hoàn thành một công việc:
1. Mở file [TIEN_DO_DO_AN.md](file:///d:/Agentic/Agentic%20Application/TIEN_DO_DO_AN.md).
2. Đổi `- [ ]` thành `- [x]` tại dòng công việc tương ứng.
3. Chạy lệnh cập nhật trong terminal:
   ```bash
   python scripts/update_progress.py
   ```
4. Script sẽ tự động tính toán lại tỷ lệ %, vẽ lại thanh tiến độ và cập nhật bảng tổng kết ngay lập tức!
