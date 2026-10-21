# SE373 · Đồ Án Cuối Kỳ: Giới Thiệu, Lộ Trình & Danh Sách Đề Tài

> **Khóa học:** SE373 — Kỹ thuật xây dựng hệ thống Agentic AI  
> **Khoa:** Công nghệ Phần mềm — FIT - HCMUS / UIT  
> **Trọng số:** Chiếm 50% điểm tổng kết môn học (thang điểm 10.0)  
> **Hình thức:** Làm việc theo nhóm 5 sinh viên  

---

## 1. Lộ Trình Thực Hiện Đồ Án (3 Phases)

```
[Phase 1: Bootstrap] ──────────► [Phase 2: Mở rộng] ──────────► [Phase 3: Hoàn thiện & Nộp]
 07/10 – 27/10 (3 tuần)           28/10 – 10/11 (2 tuần)          11/11 – 06/12 (3 tuần)
 Hạn chót: Tuần 7                 Hạn chót: Tuần 9                Hạn chót: Tuần 12
```

### 🟢 Phase 1: Bootstrap Dự Án (07/10 – 27/10 · 3 tuần · Hạn chót Tuần 7)
*Kiến thức áp dụng: Buổi 1 – 5*
- Đăng ký nhóm 5 sinh viên, chọn đề tài, danh sách use cases và phân công người sở hữu từng UC.
- Khởi tạo Git repository, cấu hình CI, phân tách codebase ứng dụng (`app/`) và codebase agent (`agent/`).
- Xây dựng Agent Loop hoàn chỉnh với $\ge 2$ tools, 1 skill chuẩn, có step logging (ghi vết từng bước).
- Hoàn thành **1 use case chạy được end-to-end** từ ứng dụng tới agent.
- Xây dựng tập kiểm thử ban đầu với $\ge 10$ eval cases.

### 🟡 Phase 2: Mở Rộng Năng Lực (28/10 – 10/11 · 2 tuần · Hạn chót Tuần 9)
*Kiến thức áp dụng: Buổi 6 – 8*
- Xây dựng pipeline **RAG có trích dẫn nguồn** (Grounding & Citation) đối soát quy chuẩn dự án.
- Cài đặt cơ chế **State Management**: Lưu task state, checkpointing, dừng và chạy tiếp (Resume), nén ngữ cảnh (Compaction) khi diff/prompt quá lớn.
- Thiết kế **Workflow LangGraph**, có điểm dừng **Human-in-the-Loop (HITL)** cho người dùng duyệt hành động.
- Đảm bảo $\ge 3$ use cases chạy hoàn hảo từ giao diện ứng dụng tới agent.

### 🔴 Phase 3: Hoàn Thiện & Nộp (11/11 – 06/12 · 3 tuần · Hạn chót Tuần 12)
*Kiến thức áp dụng: Buổi 9 – 12*
- Nâng cấp kiến trúc **Multi-Agent** chuyên biệt hoặc tích hợp giao thức **MCP (Model Context Protocol)**.
- Xây dựng cơ chế **Adaptive Memory**: Học từ phản hồi của nhóm (team feedback) để giảm cảnh báo sai (False Positives).
- Thiết lập **Security & Guardrails Harness**: Chống Prompt Injection, phân quyền an toàn Least Privilege.
- Tích hợp hệ thống **Observability & Tracing** toàn diện.
- Chạy benchmark đối sánh toàn diện trên tập Golden Eval Dataset, hoàn thiện giao diện phần mềm đạt 2.5đ.
- Viết Báo cáo đồ án chi tiết (PDF), quay Video demo chất lượng cao và chuẩn bị slide bảo vệ.

---

## 2. Hình Thức Trình Bày & Bảo Vệ Đồ Án

Quy trình đánh giá gồm 2 buổi độc lập:

```
┌──────────────────────────────────────────────┐
│  BUỔI 1: Trình bày trong nhóm nhỏ (Pool)    │
│  - 1 Pool gồm 10 nhóm                        │
│  - 1 Giảng viên Thực hành (GVTH) phụ trách   │
│  - Mỗi nhóm demo & bảo vệ chi tiết từng UC   │
│  - Mỗi Pool chọn ra 2 đề tài xuất sắc nhất   │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  BUỔI 2: Trình bày chung khảo trước cả lớp   │
│  - Gồm 10 đề tài xuất sắc nhất từ các Pool   │
│  - Demo & thuyết trình trước toàn thể GV & SV│
│  - Vinh danh các sản phẩm Agentic AI tiêu biểu│
└──────────────────────────────────────────────┘
```

> [!NOTE]
> **Quy định vấn đáp cá nhân:** Mỗi thành viên trong nhóm phải trình bày được use case mình sở hữu và trả lời câu hỏi phản biện về kiến trúc Agent = Model + Harness. Điểm cá nhân được nhân theo hệ số vấn đáp ($0.0 - 1.0$).

---

## 3. Cơ Cấu Tính Điểm Đồ Án Cuối Kỳ

$$\text{Tổng điểm đồ án (10.0)} = \text{Điểm Agent (Tối đa 7.5)} + \text{Điểm Phần mềm (Tối đa 2.5)}$$

### 3.1. Phần Agent (Tối đa 7.5 điểm)
- Yêu cầu tối thiểu **5 use cases**, mỗi use case trị giá **1.5 điểm** ($5 \times 1.5 = 7.5$ điểm).
- Mỗi use case được chấm theo 3 tiêu chí:
  1. **Chức năng (0.5 điểm):** Chạy đúng tiêu chí nghiệp vụ đề ra trên các test case thực tế.
  2. **Thiết kế Harness (0.5 điểm):** Đúng kỹ thuật kiến trúc harness tương ứng với các mảng kiến thức K chính.
  3. **Kiểm chứng (0.5 điểm):** Có bộ eval test cases, đo lường được kết quả và hiển thị trace rõ ràng.
- **Yêu cầu phủ 8 mảng kiến thức (K1–K8):** Danh sách use cases nộp phải bao quát toàn diện K1–K8. Thiếu mỗi mảng kiến thức bị **trừ 0.5 điểm**.

### 3.2. Phần Mềm (Tối đa 2.5 điểm)
- Hình thức tự chọn: **Web Application, Desktop App hoặc CLI**, nhưng **bắt buộc phải tích hợp agent thật**.
- Tiêu chí đánh giá:
  - **Sáng tạo (0.5 điểm):** Ý tưởng khác biệt, giải quyết đúng nỗi đau người dùng, trải nghiệm tương tác mới mẻ.
  - **Độ phức tạp kỹ thuật (0.75 điểm):** Kiến trúc phân tầng, xử lý bất đồng bộ, stream log mượt mà.
  - **Độ hoàn thiện UI/UX và độ ổn định (0.75 điểm):** Giao diện chỉn chu, phản hồi nhanh, không crash khi demo.
  - **Khối lượng công việc (0.5 điểm):** Khối lượng code tương xứng với nhóm 5 người làm trong 8 tuần.

---

## 4. Danh Sách 10 Đề Tài Đăng Ký Đồ Án Cuối Kỳ

| # | Tên Đề Tài | Mô Tả Trọng Tâm Nghiệp Vụ | GVTH Phụ Trách |
| :-: | :--- | :--- | :--- |
| **1** | **Coding Agent** | Phân loại issue, sửa bug theo vòng lặp chạy test, làm tính năng nhiều bước; Reviewer Agent kiểm tra trước khi bàn giao code. | ThS. Nguyễn Hiếu Nghĩa |
| **2** | **Code Review Agent** *(Đề tài đang chọn)* | Comment trực tiếp lên Pull Request kèm mức độ nghiêm trọng (severity) và gợi ý sửa code (suggestion patch); nhiều reviewer chuyên biệt; học từ phản hồi của team. | **ThS. Nguyễn Ngọc Quí** |
| **3** | **Helpdesk Agent** | Chăm sóc khách hàng: trả lời có trích dẫn nguồn, tra cứu đơn hàng, tự động tạo ticket, chuyển giao cho nhân viên thật (Human Handoff) khi cần. | ThS. Quan Chí Khánh An |
| **4** | **GEO Content Writer Agent** | Nghiên cứu nguồn tài liệu, viết bài chuẩn giọng thương hiệu, kiểm chứng số liệu thực tế, đo lường mức độ được AI trích dẫn. | ThS. Dương Nguyễn Phương Nam |
| **5** | **Interview Agent** | Lên kịch bản phỏng vấn từ Job Description (JD) và CV ứng viên, phỏng vấn nhiều lượt, chấm điểm theo rubric có dẫn chứng; con người ra quyết định tuyển dụng cuối cùng. | ThS. Dương Nguyễn Phương Nam |
| **6** | **IELTS Learning Agent** | Chấm bài Writing theo tiêu chí Band Descriptors, thi thử Speaking, sinh bài đọc/nghe theo cấp độ, lập kế hoạch học tập theo điểm yếu của học viên. | ThS. Nguyễn Thị Hoàng Anh |
| **7** | **Business Ops Agent** | Tương tự hệ thống Hermes: dựng sẵn đội ngũ agent các phòng ban (Sales, Marketing, HR, Kế toán, CSKH, Vận hành) có Leader Agent điều phối liên phòng ban. | ThS. Nguyễn Hiếu Nghĩa |
| **8** | **Tour Guide Agent** | Lên lịch trình du lịch bằng tool thời tiết và bản đồ; thuyết minh điểm đến Việt Nam song ngữ; tự động điều chỉnh lịch trình khi gặp sự cố ngoại cảnh. | ThS. Nguyễn Thị Hoàng Anh |
| **9** | **Analytics Agent** | Người dùng hỏi bằng ngôn ngữ tự nhiên, agent tự viết và thực thi truy vấn SQL, vẽ biểu đồ trực quan, phân tích nguyên nhân biến động dữ liệu; chỉ có quyền đọc (Read-only). | ThS. Quan Chí Khánh An |
| **10** | **AI Training Agent** | Cùng người dùng xây dựng kịch bản tình huống (scenario), đóng vai các nhân vật để người học luyện kỹ năng giao tiếp/xử lý tình huống, sau đó chấm điểm và đưa ra feedback cải thiện. | ThS. Nguyễn Ngọc Quí |
