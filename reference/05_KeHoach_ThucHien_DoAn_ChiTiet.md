# SE373 · KẾ HOẠCH CHI TIẾT THỰC HIỆN ĐỒ ÁN CUỐI KỲ
## ĐỀ TÀI SỐ 2: CODE REVIEW AGENT

> **Học phần:** SE373 - Kỹ thuật xây dựng hệ thống Agentic AI (UIT)  
> **Giảng viên hướng dẫn:** ThS. Nguyễn Ngọc Quí  
> **Mục tiêu điểm số:** 10.0 / 10.0 (7.5 điểm Agent + 2.5 điểm Phần mềm)  
> **Quy mô nhóm:** 5 sinh viên (mỗi sinh viên sở hữu và bảo vệ 1 Use Case)

---

## MỤC LỤC
1. [Phân bổ 5 Use Case Phủ Đủ 8 Mảng Kiến Thức (K1–K8)](#1-phân-bổ-5-use-case-phủ-đủ-8-mảng-kiến-thức-k1k8)
2. [Lộ trình 3 Phase: Thực hiện từng bước](#2-lộ-trình-3-phase-thực-hiện-từng-bước)
3. [Chiến lược Benchmark & Kiểm thử (Evaluation Harness)](#3-chiến-lược-benchmark--kiểm-thử-evaluation-harness)
4. [Kiến trúc Thư mục Codebase Chuẩn](#4-kiến-trúc-thư-mục-codebase-chuẩn)
5. [Danh mục Đầu ra Cuối cùng (Final Deliverables Checklist)](#5-danh-mục-đầu-ra-cuối-cùng-final-deliverables-checklist)

---

## 1. Phân bổ 5 Use Case Phủ Đủ 8 Mảng Kiến Thức (K1–K8)

Để đạt trọn **7.5 điểm Agent** và không bị trừ điểm do thiếu mảng kiến thức nào, 5 thành viên trong nhóm sẽ sở hữu 5 Use Case được thiết kế phủ kín 8 mảng kiến thức:

| Mã UC | Tên Use Case & Mô tả cốt lõi | Sinh viên sở hữu | Lớp Harness chính | Mảng kiến thức phủ | Phase hoàn thành |
| :---: | :--- | :---: | :--- | :---: | :---: |
| **UC1** | **Automated Inline PR Review with Severity & Fixes:** Bóc tách git diff, phát hiện lỗi kèm mức độ (`CRITICAL`, `HIGH`...) và sinh khối sửa code GitHub ` ```suggestion `. | Thành viên 1 | `Context`, `Tools`, `Skills`, `Logging` | **K1, K2, K3** | **Phase 1** |
| **UC2** | **Project Coding Standards Verification via RAG:** Đối chiếu code thay đổi với tài liệu quy ước riêng của repository (architecture guide, naming conventions) kèm trích dẫn nguồn chuẩn xác. | Thành viên 2 | `Retrieval (RAG)`, `Context Compression` | **K4** | **Phase 2** |
| **UC3** | **Stateful Review & Human-in-the-Loop (HITL) Approval:** Lưu vết tiến trình review qua checkpoints (dừng và tiếp tục khi PR có push mới); người dùng duyệt/chỉnh sửa comment trước khi post lên GitHub. | Thành viên 3 | `State`, `Workflow`, `Human Approval` | **K5, K6** | **Phase 2** |
| **UC4** | **Multi-Agent Specialist Review Committee (LangGraph / MCP):** Phối hợp 3 reviewer chuyên sâu (Security, Performance, Logic) qua đồ thị LangGraph; kiểm định an toàn và trực quan hóa trace. | Thành viên 4 | `Workflow (LangGraph)`, `Handoff`, `Permission`, `Trace` | **K7** | **Phase 3** |
| **UC5** | **Team Feedback Learning & Adaptive Memory:** Thu thập phản hồi thực tế của lập trình viên (accept/reject suggestion, comment thảo luận) để cập nhật Long-term Memory, tự động giảm False Positives theo thời gian. | Thành viên 5 | `Memory`, `Verification`, `Safety Guardrails` | **K8** | **Phase 3** |

---

## 2. Lộ trình 3 Phase: Thực hiện từng bước

```
                 LỘ TRÌNH 3 PHASE (TUẦN 5 ĐẾN TUẦN 12)
   Phase 1: Bootstrap             Phase 2: Mở rộng              Phase 3: Hoàn thiện
  [07/10 ───► 27/10]             [28/10 ───► 10/11]            [11/11 ───► 06/12]
  • Khởi tạo Repo & CI           • RAG trích dẫn nguồn         • Multi-Agent LangGraph
  • Agent Loop (2 tools, 1 skill)• State Checkpoint/Resume     • MCP Server tích hợp
  • UC1 chạy end-to-end          • Human-in-the-loop duyệt     • Safety Guardrails
  • 10 Eval test cases           • Hoàn thành UC1, UC2, UC3    • 5 Use cases hoàn chỉnh
  • Gắn Tag v1.0 & Video         • Gắn Tag v2.0 & Video        • Báo cáo & Video Demo
```

### 🔴 PHASE 1: BOOTSTRAP DỰ ÁN (07/10 – 27/10 · 3 tuần · Hạn chót Tuần 7)
*Mục tiêu: Dựng nền móng vững chắc, chạy thông luồng 1 use case đầu tiên từ ứng dụng tới agent với log chi tiết.*

*   **Tuần 5 (07/10 – 13/10): Khởi tạo hạ tầng & Phân chia trách nhiệm**
    *   [x] Khởi tạo Git repository, cấu hình `.gitignore` (chặn tuyệt đối commit file `.env` hoặc file chứa API key).
    *   [x] Cấu hình CI workflow cơ bản (GitHub Actions kiểm tra linting và pytest).
    *   [x] Thiết kế cấu trúc thư mục phân tách độc lập: `agent/` (harness & model loop) và `app/` (giao diện UI/API).
    *   [x] Khóa danh sách nhóm 5 thành viên và đăng ký 5 Use Case với GVTH ThS. Nguyễn Ngọc Quí.
*   **Tuần 6 (14/10 – 20/10): Xây dựng Agent Core & Tools**
    *   [ ] Lập trình 2 Tools cơ bản trong `agent/tools/`:
        1. `GitDiffReader`: Phân tích git patch, trích xuất danh sách file thay đổi, số dòng thêm/bớt.
        2. `FileContextReader`: Đọc toàn bộ nội dung file mã nguồn xung quanh diff để hiểu ngữ cảnh.
    *   [ ] Tích hợp gói skill `skills/pr-code-review/` chuẩn mực.
    *   [ ] Xây dựng **Agent Loop cơ bản (ReAct)** với Pydantic structured output cho `CodeIssue` và `ReviewVerdict`.
    *   [ ] Thiết lập cơ chế **Step Logging**: ghi log chi tiết từng bước (Step number, Thought, Tool Call, Observation, Latency, Token count).
*   **Tuần 7 (21/10 – 27/10): Hoàn thiện UC1, Benchmark 10 cases & Nộp Phase 1**
    *   [ ] Nối Agent vào ứng dụng (giao diện CLI hoặc Web UI đơn giản xem diff và nhận review).
    *   [ ] Xây dựng bộ **≥ 10 Eval Test Cases** (10 file git diff thật có bug và lỗi bảo mật).
    *   [ ] Chạy benchmark Phase 1, xuất báo cáo đo lường độ chính xác.
    *   [ ] Quay video demo ngắn (3–5 phút) chứng minh agent loop chạy thật, có log từng bước.
    *   [ ] Gắn git tag `phase-1-bootstrap` và nộp lên hệ thống.

---

### 🟡 PHASE 2: MỞ RỘNG NĂNG LỰC (28/10 – 10/11 · 2 tuần · Hạn chót Tuần 9)
*Mục tiêu: Đưa tri thức repository vào qua RAG trích dẫn, quản lý trạng thái có thể dừng/chạy tiếp và bước người duyệt.*

*   **Tuần 8 (28/10 – 03/11): RAG Coding Standards & Context Management (UC2)**
    *   [ ] Xây dựng pipeline RAG trong `agent/rag/`:
        *   Chunking và index tài liệu quy ước coding của repo (markdown guidelines, style guides).
        *   Embedding và lưu trữ vào Vector DB cục bộ (ChromaDB hoặc FAISS).
        *   Truy xuất quy chuẩn liên quan kèm **Citation (trích dẫn tên file, đoạn văn bản)** trong review comment.
    *   [ ] Kỹ thuật nén context: Lọc bỏ các file lock/asset thừa trong PR diff để tránh tràn context window.
*   **Tuần 9 (04/11 – 10/11): State Checkpoint/Resume & Human-in-the-Loop (UC3)**
    *   [ ] Tích hợp **LangGraph StateGraph**:
        *   Quản lý State: `pr_metadata`, `diff_chunks`, `analysis_state`, `pending_comments`.
        *   Hỗ trợ Checkpointing: Khi PR có commit mới được push, agent dừng, lưu checkpoint vào SQLite và resume từ diff mới.
    *   [ ] Thiết lập cơ chế **Human-in-the-Loop (HITL)**:
        *   Node dừng chờ phê duyệt (`interrupt_before=["post_to_github"]`).
        *   Giao diện hiển thị danh sách comment gợi ý, cho phép lập trình viên sửa/duyệt/bỏ qua trước khi phát hành lên PR.
    *   [ ] Đảm bảo **≥ 3 use case (UC1, UC2, UC3)** chạy trơn tru end-to-end.
    *   [ ] Gắn git tag `phase-2-expansion` và nộp video demo Phase 2.

---

### 🟢 PHASE 3: HOÀN THIỆN VÀ NỘP (11/11 – 06/12 · 3 tuần · Hạn chót Tuần 12)
*Mục tiêu: Nâng cấp kiến trúc Multi-Agent/MCP, học từ phản hồi team, kiểm thử an toàn, trace hoàn chỉnh và bảo vệ đồ án.*

*   **Tuần 10 (11/11 – 17/11): Multi-Agent Committee / MCP Integration (UC4)**
    *   [ ] Xây dựng hội đồng reviewer chuyên biệt (Multi-Agent Sub-graphs):
        *   `SecurityAgent`: Chuyên sâu quét OWASP, secrets, injection.
        *   `PerformanceAgent`: Chuyên sâu phát hiện N+1 query, resource leaks, vòng lặp $O(N^2)$.
        *   `LogicStyleAgent`: Chuyên sâu bắt null-pointer, off-by-one, convention.
        *   `LeadReviewerAgent`: Điều phối, tổng hợp và loại bỏ comment trùng lặp.
    *   [ ] Triển khai giao thức **MCP (Model Context Protocol)** để kết nối agent với GitHub MCP server / DB inspector.
*   **Tuần 11 (18/11 – 24/11): Team Feedback Learning Loop & Safety Guardrails (UC5)**
    *   [ ] Xây dựng cơ chế **Adaptive Memory**:
        *   Ghi nhận phản hồi của developer: reaction 👍/👎, trạng thái comment được resolve hay ignore.
        *   Cập nhật quy tắc loại trừ vào Long-term Memory để giảm thiểu triệt để False Positives ở các PR tương lai.
    *   [ ] Thiết lập **Security & Guardrails Harness**:
        *   Chặn prompt injection ẩn trong code commit.
        *   Phân quyền read-only đối với repository (không được quyền push code/merge PR trái phép).
    *   [ ] Tích hợp Observability & Tracing (LangSmith hoặc OpenTelemetry/Phoenix) để xem full trace đồ thị.
*   **Tuần 12 (25/11 – 06/12): Benchmark Toàn diện, Báo cáo & Quay Video Chung cuộc**
    *   [ ] Chạy lại toàn bộ tập Eval benchmark đối sánh kết quả qua 3 Phase.
    *   [ ] Hoàn thiện Web Dashboard (`app/server.py` FastAPI + Modern Dark Theme UI) tích hợp 3 tính năng: PR Review Live, HITL Approval Gate (UC-07), Trace Flow & Benchmark Visualization (đạt trọn 2.5đ phần mềm).
    *   [ ] Chuẩn hóa CLI Runner (`app/cli.py`) phục vụ chạy batch eval và tích hợp tự động vào CI/CD pipeline.
    *   [ ] Viết Báo cáo đồ án đầy đủ (PDF) kèm cấu trúc minh chứng 8 mảng kiến thức K1–K8.
    *   [ ] Quay Video demo chung cuộc chất lượng cao.
    *   [ ] Gắn git tag `phase-3-final` và chuẩn bị slide bảo vệ trước hội đồng.

---

## 3. Chiến lược Benchmark & Kiểm thử (Evaluation Harness)

Hệ thống đánh giá tự động là điều kiện tiên quyết để đạt **0.5 điểm Kiểm chứng** cho mỗi use case.

### 3.1. Thiết kế Tập Golden Eval Dataset (Tối thiểu 15–20 cases)
Tập dữ liệu kiểm thử được tổ chức trong thư mục `eval/dataset/`:
*   **Group 1: Lỗi Bảo mật (Security - 5 cases):** PR chứa SQL Injection, Hardcoded JWT Secret, Path Traversal, Insecure Regex, Missing Auth check.
*   **Group 2: Lỗi Hiệu năng (Performance - 4 cases):** PR chứa vòng lặp N+1 query ORM, rò rỉ File Handle, Memory Leak do closure, thiếu chỉ mục.
*   **Group 3: Lỗi Logic & Biên (Logic & Bugs - 4 cases):** PR chứa Null pointer exception, Off-by-one index, so sánh sai kiểu dữ liệu, unhandled promise.
*   **Group 4: Quy chuẩn Repo (Standards & Style - 4 cases):** PR vi phạm tài liệu convention nội bộ của nhóm (được RAG đối chiếu).
*   **Group 5: Negative / Clean PRs (3 cases):** PR hoàn toàn sạch và chuẩn mực $\rightarrow$ Agent phải trả về `APPROVE` mà không sinh comment rác (False Positive).

### 3.2. Chỉ số Đo lường (Evaluation Metrics)

| Chỉ số | Cách tính | Mục tiêu kỳ vọng | Ý nghĩa đánh giá |
| :--- | :--- | :---: | :--- |
| **Precision (Độ chuẩn xác)** | $\frac{\text{Lỗi bắt đúng}}{\text{Tổng số lỗi Agent báo}}$ | **$\ge 85\%$** | Đo lường tỷ lệ không gây phiền toái cho developer (ít cảnh báo rác). |
| **Recall (Độ bao phủ)** | $\frac{\text{Lỗi bắt đúng}}{\text{Tổng số lỗi thực tế trong Golden Set}}$ | **$\ge 80\%$** | Đảm bảo không bỏ sót các lỗi bảo mật và logic quan trọng. |
| **False Positive Rate** | $\frac{\text{Cảnh báo sai}}{\text{Tổng số cảnh báo}}$ | **$\le 15\%$** | Đo khả năng phân biệt code đúng/sai. |
| **Suggestion Syntax Rate** | $\frac{\text{Số suggestion hợp lệ}}{\text{Tổng số suggestion sinh ra}}$ | **$100\%$** | Đo tính chuẩn xác cơ học (chạy qua parser/linter không bị lỗi cú pháp). |
| **Line Accuracy** | $\frac{\text{Số comment trúng đúng dòng}}{\text{Tổng số comment}}$ | **$100\%$** | Comment phải trỏ chính xác vào dòng bị thay đổi trong diff. |
| **Average Latency & Cost** | Thời gian chạy và số token tiêu thụ/PR | **$< 30s$ / PR** | Đảm bảo tính khả thi khi tích hợp vào CI/CD thực tế. |

### 3.3. Script Tự động Chạy Benchmark: `eval/run_benchmark.py`
Script tự động nạp toàn bộ test cases, kích hoạt agent, so khớp kết quả với `ground_truth.json`, xuất bảng Markdown so sánh đối chứng giữa các phiên bản.

---

## 4. Kiến trúc Thư mục Codebase Chuẩn

```
agentic-code-reviewer/
├── .github/
│   └── workflows/
│       └── ci.yml                 # CI test & linting tự động
├── agent/                         # CODEBASE AGENT (Harness + Orchestration)
│   ├── harness/
│   │   ├── loop.py                # Vòng lặp agent (ReAct, LoopDetector)
│   │   ├── state.py               # Quản lý State & SQLite Checkpoint
│   │   ├── termination.py         # 5 Điều kiện dừng
│   │   └── verification.py        # Thẩm định kết quả trước khi post
│   ├── graph/
│   │   ├── workflow.py            # LangGraph StateGraph điều phối
│   │   └── nodes/                 # Các node: diff_parser, security, reviewer, hitl
│   ├── tools/
│   │   ├── diff_reader.py         # Tool đọc git diff
│   │   ├── context_reader.py      # Tool đọc ngữ cảnh file
│   │   ├── rag_search.py          # Tool tìm kiếm coding standards
│   │   └── github_poster.py       # Tool post comment lên PR
│   ├── memory/
│   │   └── team_memory.py         # Vector store lưu conventions và dev feedback
│   └── skills/
│       └── pr-code-review/        # Gói Skill chuẩn (SKILL.md, references, scripts)
├── app/                           # CODEBASE ỨNG DỤNG (UI / API / CLI)
│   ├── api/                       # FastApi backend (Webhook receiver từ GitHub)
│   ├── ui/                        # Web Dashboard (xem diff, HITL duyệt comment)
│   └── cli/                       # CLI tool chạy review cục bộ
├── eval/                          # HARNESS KIỂM CHỨNG & BENCHMARK
│   ├── dataset/                   # Bộ test cases git diff mẫu + ground truth
│   ├── run_benchmark.py           # Script tự động tính Precision, Recall, FPR
│   └── results/                   # Báo cáo kết quả benchmark qua 3 phase
├── reference/                     # TÀI LIỆU LÝ THUYẾT MÔN HỌC (Đã đóng gói)
├── .env.example                   # Mẫu cấu hình biến môi trường (KHÔNG LỘ KEY)
├── requirements.txt               # Danh sách thư viện Python
└── README.md                      # Hướng dẫn cài đặt và chạy ứng dụng
```

---

## 5. Danh mục Đầu ra Cuối cùng (Final Deliverables Checklist)

Khi kết thúc Phase 3 để chuẩn bị bảo vệ trước lớp, nhóm cần hoàn tất 100% các hạng mục sau:

- [ ] **Mã nguồn Git chuẩn mực:**
  - Repo sạch sẽ, CI xanh, có file `.env.example`, **tuyệt đối không lộ API key** (-1.0đ nếu vi phạm).
  - Có đủ 3 tag tương ứng 3 phase: `phase-1-bootstrap`, `phase-2-expansion`, `phase-3-final`.
- [ ] **5 Use Cases chạy thực tế:**
  - Mỗi use case có tài liệu kiến trúc, chứng minh đủ 3 tiêu chí: Chức năng (0.5đ), Thiết kế Harness (0.5đ), Kiểm chứng (0.5đ).
  - Phủ trọn vẹn 8 mảng kiến thức K1–K8 (không bị trừ 0.5đ/mảng).
- [ ] **Hệ thống Kiểm thử & Trace:**
  - Tập eval benchmark đối sánh rõ rệt độ cải thiện giữa Phase 1, Phase 2 và Phase 3.
  - Giao diện xem trace trực quan (LangSmith trace URL hoặc file trace log jsonl).
- [ ] **Sản phẩm Phần mềm (UI/UX - 2.5đ):**
  - Giao diện **Web Dashboard** (FastAPI + Modern UI) trực quan: hỗ trợ developer duyệt/sửa/từ chối comment (HITL UC-07), theo dõi live trace graph của agent (K8), và bảng thống kê kết quả benchmark (K7).
  - Công cụ **CLI Runner** (`app/cli.py`): gọn nhẹ, ổn định để chạy local và tích hợp vào CI/CD.
- [ ] **Báo cáo Đồ án & Thuyết trình:**
  - Báo cáo đồ án chi tiết (file PDF) trình bày bài toán, kiến trúc hệ thống, 12 lớp harness, kết quả benchmark.
  - Slide thuyết trình và Video demo độ phân giải cao giới thiệu toàn bộ tính năng.
  - Mỗi thành viên nắm vững use case mình phụ trách để trả lời vấn đáp cá nhân (hệ số 0.0 – 1.0).
