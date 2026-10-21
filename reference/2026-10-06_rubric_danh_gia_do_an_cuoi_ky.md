---
title: "SE373 — Rubric đánh giá đồ án cuối kỳ (A4)"
course: SE373 Agentic AI Engineering
created: 2026-10-06
confidence: draft
stage: "BẢN NHÁP v3 — chấm theo use case ngang điểm (1,5đ/UC, trần 7,5đ); phần mềm tối đa 2,5đ; nhóm 5 SV"
supersedes: raw/hcmus/Courses/AgenticAIEngineering/DoAnCuoiKy/2026-10-06_rubric_danh_gia_do_an_cuoi_ky_v2.md
sources:
  - raw/hcmus/Courses/AgenticAIEngineering/Curriculum/SE373 - Kỹ thuật xây dựng hệ thống Agentic AI.md (Bảng 8, 9, 10, 11, mục 6)
  - raw/hcmus/Courses/AgenticAIEngineering/00_Course_Overview.md (mục 5, 7)
---

# SE373 — Rubric Đánh Giá Đồ Án Cuối Kỳ (A4)

Đồ án cuối kỳ (A4) chiếm **50% điểm môn học**. Bài làm theo nhóm 5 sinh viên (khoảng 50 nhóm cho cả môn).

---

## 1. Cấu trúc Điểm

| Phần | Nội dung | Điểm |
| :--- | :--- | :---: |
| **I. Phần mềm** | Ứng dụng có tích hợp agent (desktop, web hoặc CLI, nhóm tự chọn) | Tối đa **2,5** |
| **II. Agent** | Tổng điểm các use case nhóm hoàn thành, mỗi UC tối đa 1,5 điểm | Tối đa **7,5** |
| **Tổng điểm nhóm** | | **10,0** |

$$\text{Điểm cá nhân} = \text{Điểm nhóm} \times \text{Hệ số vấn đáp (mục 6)}$$

*Điều kiện bắt buộc và các khoản trừ điểm xem tại mục 5.*

**Nguyên tắc:**
- **Phần I:** Chấm sản phẩm phần mềm bao quanh agent. Nhóm được tự do sáng tạo, nhưng phần này không vượt quá 2,5 điểm để giữ trọng tâm vào kỹ thuật agent.
- **Phần II:** Chấm trực tiếp năng lực của agent qua từng use case. Mỗi use case có trọng số bằng nhau (1,5 điểm), độc lập với nhau, có thể do một sinh viên chịu trách nhiệm chính.

---

## 2. Quy Định Chung về Use Case (Phần II)

### 2.1. Số lượng và Cách Tính Điểm
- Nhóm nộp **tối thiểu 5 use case**.
- $5 \times 1,5 = 7,5$ điểm (đủ trần phần agent).
- Nhóm có thể làm thêm use case (ví dụ 6 hoặc 7 UC). Điểm phần II là tổng điểm của các UC đạt được, lấy trần 7,5 điểm. Việc làm thêm giúp bù điểm nếu một số UC không đạt điểm tối đa.

### 2.2. 8 Mảng Kiến Thức và Quy Tắc Phủ (K1–K8)
Mỗi UC trong mô tả đề tài được gắn 1–3 mảng kiến thức chính. Mảng chính được chấm ở tiêu chí U2 của UC đó.

| Mã | Mảng kiến thức | Buổi học | CĐRMH |
| :--- | :--- | :---: | :---: |
| **K1** | Tích hợp model, structured output, agent loop, kiến trúc model + harness | 2, 3, 4 | G2.1, G3.1 |
| **K2** | Tool use và agent skills | 5 | G2.3, G3.2 |
| **K3** | RAG / knowledge harness | 6 | G3.3, G2.2 |
| **K4** | Memory, state, context | 7 | G2.2 |
| **K5** | Workflow orchestration, human-in-the-loop | 8 | G4.1 |
| **K6** | Multi-agent hoặc MCP | 10 | G4.2 |
| **K7** | Verification và evaluation | 9, 11 | G5.1 |
| **K8** | Security, governance, observability | 11, 12 | G6.1, G6.2 |

> [!IMPORTANT]
> **Quy tắc phủ bắt buộc:** Tập các use case nhóm nộp **phải bao quát đủ cả 8 mảng K1–K8**. Mỗi mảng kiến thức bị thiếu trong tập UC nộp sẽ bị **trừ 0,5 điểm** ở phần II.

### 2.3. Trách Nhiệm Cá Nhân
- Mỗi sinh viên trong nhóm phải là **chủ sở hữu chính (owner)** của ít nhất 1 use case: chịu trách nhiệm thiết kế harness, cài đặt và xây dựng bộ eval cho UC đó.
- Bảng phân công ghi rõ trong README và báo cáo. Điểm vấn đáp của mỗi cá nhân bắt đầu từ UC mình sở hữu.

### 2.4. Yêu Cầu Nền Chung (Áp dụng cho Toàn Hệ Thống)
Các yêu cầu này không có điểm riêng nhưng được kiểm tra tự động ở Vòng 1. Vi phạm sẽ bị trừ điểm hoặc hạ điểm U2/U3:

| Mã HR | Nội dung yêu cầu nền |
| :--- | :--- |
| **HR-01** | Gọi LLM API hoặc model local; báo cáo nêu rõ giới hạn của model đã chọn. |
| **HR-02** | Có workflow từ 3 node trở lên, có điều kiện dừng rõ ràng. |
| **HR-03** | Có sơ đồ kiến trúc `Agent = Model + Harness`, chỉ rõ từ 4 lớp harness trở lên; có bảng failure modes và cơ chế giảm rủi ro. |
| **HR-04** | Có ít nhất 1 công cụ ngoài; có ít nhất 2 skill dùng lại được với contract đầy đủ. |
| **HR-05** | Mọi lần chạy đều có log/trace: input, output, tool call, skill invocation, lỗi, quyết định. |
| **HR-06** | Tập eval chung chạy được bằng 1 lệnh; tổng tối thiểu $5 \times \text{Số UC} + 5 \text{ cases tấn công}$ (ví dụ 5 UC thì tối thiểu 30 cases); chạy regression ít nhất 2 lần (trước và sau cải tiến). |
| **HR-07** | Repo có README, `.env.example`, báo cáo kỹ thuật, video demo, bảng phân công sở hữu từng UC, mục minh bạch sử dụng AI và trích dẫn nguồn. |

---

## 3. Rubric Phần I — Phần Mềm (Tối đa 2,5 điểm)

Hình thức tự chọn: **Desktop App, Web App hoặc CLI App**. Ứng dụng phải **tích hợp agent thật** (người dùng thao tác trên app, app gọi agent, hiển thị tiến trình và kết quả). App chỉ là khung chat bọc ngoài API LLM sẽ không được tính.

Mỗi tiêu chí chấm theo 4 mức: **Giỏi (100%) · Khá (75%) · Trung bình (50%) · Yếu (0–25%)**.

| Tiêu chí | Điểm | Giỏi (100%) | Khá (75%) | Trung bình (50%) | Yếu (0–25%) |
| :--- | :---: | :--- | :--- | :--- | :--- |
| **I.1. Sáng tạo** | 0,5 | Ý tưởng sản phẩm khác biệt, giải quyết đúng nỗi đau người dùng; đưa agent vào trải nghiệm theo cách mới (không chỉ là khung chat). | Có điểm khác biệt rõ ở một vài tính năng hoặc cách tương tác. | Đúng đề tài nhưng cách làm phổ biến, ít điểm mới. | Sao chép mẫu có sẵn, không có dấu ấn riêng. |
| **I.2. Độ phức tạp kỹ thuật** | 0,75 | Kiến trúc đa tầng rõ ràng (UI, backend, agent runner, storage); tích hợp mượt nhiều nguồn dữ liệu hoặc tool ngoài; xử lý bất đồng bộ/stream tốt. | Có kiến trúc phân tầng nhưng xử lý bất đồng bộ hoặc tích hợp ngoài còn đơn giản. | Ứng dụng nguyên khối (monolithic) đơn giản, ít thành phần phối hợp. | Chỉ là script bọc lỏng lẻo quanh agent loop. |
| **I.3. Độ hoàn thiện (UI/UX, ổn định)** | 0,75 | Giao diện chỉn chu, phản hồi nhanh, có thông báo trạng thái agent; xử lý lỗi mềm dẻo; không crash trong suốt quá trình demo. | Giao diện dùng được; thỉnh thoảng có lỗi giao diện nhỏ nhưng không crash luồng chính. | Giao diện thô, trải nghiệm người dùng chưa mượt; dễ bị treo khi agent xử lý lâu. | Hay crash, lỗi vặt liên tục, demo gián đoạn. |
| **I.4. Khối lượng công việc** | 0,5 | Khối lượng code phần mềm tương xứng với nhóm 5 người làm trong 8 tuần; có lịch sử commit đều đặn của các thành viên. | Khối lượng khá, phần lớn tính năng cam kết được hoàn thành. | Khối lượng ít so với quy mô nhóm; một vài tính năng quan trọng chưa xong. | Sản phẩm quá sơ sài, làm đối phó vào những ngày cuối. |

---

## 4. Rubric Phần II — Agent (Tối đa 7,5 điểm)

Mỗi use case được chấm tối đa **1,5 điểm**, chia làm 3 tiêu chí:
- **U1. Chức năng (0,5đ):** UC có chạy đúng nghiệp vụ không?
- **U2. Thiết kế Harness (0,5đ):** Các mảng K chính gắn với UC được làm đúng kỹ thuật đến đâu?
- **U3. Kiểm chứng (0,5đ):** Đo lường bằng eval dataset, trace và số liệu thực nghiệm.

### 4.1. Bảng Tiêu Chí Chấm Mỗi Use Case (1,5đ / UC)

| Tiêu chí | Điểm | Giỏi (100%) | Khá (75%) | Trung bình (50%) | Yếu (0–25%) |
| :--- | :---: | :--- | :--- | :--- | :--- |
| **U1. Chức năng** | 0,5 | Đạt mọi tiêu chí chấp nhận; demo trực tiếp ổn định trên các test cases thực tế. | Đạt phần lớn tiêu chí; còn một số lỗi nhỏ ở case biên. | Chỉ chạy được luồng chuẩn (happy path); nhiều tiêu chí chấp nhận chưa đạt. | Không chạy được, không có bằng chứng, hoặc kết quả do code cứng (hardcoded). |
| **U2. Thiết kế Harness** | 0,5 | Đạt mức **Giỏi** của mọi mảng K chính gắn với UC (chi tiết mục 4.2). | Đạt mức Khá của các mảng K chính; có giải thích hợp lý về trade-off. | Có làm nhưng mang tính hình thức, chưa đúng kỹ thuật của mảng K. | Thiết kế sai nguyên lý, hoặc bỏ qua hoàn toàn mảng K yêu cầu. |
| **U3. Kiểm chứng** | 0,5 | $\ge 5$ eval case riêng cho UC (nằm trong tập chung); có metric định lượng; có trace chi tiết; phân tích được ít nhất 1 ca thất bại. | Đủ 5 eval case và metric chính; phân tích thất bại còn sơ sài. | Ít hơn 5 eval case; đánh giá thủ công là chính, thiếu số liệu. | Không có eval case cho UC; không đo lường được. |

### 4.2. Khung Đánh Giá Mảng Kiến Thức K1–K8 (Áp dụng cho U2)

* **K1. Model & Agent Loop:**
  * *Giỏi:* Structured output bằng Pydantic/Zod schema có validate chặt chẽ; vòng lặp ReAct có giới hạn số bước và cơ chế thoát an toàn; xử lý retry khi model trả về sai định dạng.
* **K2. Tool Use & Skills:**
  * *Giỏi:* Tool có schema rõ ràng, kiểm tra kiểu dữ liệu đầu vào/ra; xử lý lỗi tool mượt mà; skill được đóng gói tái sử dụng với contract tường minh.
* **K3. RAG / Knowledge Harness:**
  * *Giỏi:* Ingestion pipeline có chunking cấu trúc kèm metadata phong phú; Hybrid Search kết hợp Reranking; câu trả lời bám sát nguồn (grounded) có trích dẫn kiểm chứng được; có xử lý trường hợp không tìm thấy dữ liệu (abstention).
* **K4. Memory, State, Context:**
  * *Giỏi:* Lưu task state và log tiến trình; resume được sau khi gián đoạn; chiến lược compaction bảo toàn ràng buộc và mục tiêu; có quy định xóa/thu hồi dữ liệu cá nhân.
* **K5. Workflow Orchestration & HITL:**
  * *Giỏi:* StateGraph phân nhánh rõ ràng; có điểm dừng Human-in-the-Loop (HITL) cho phép con người duyệt/chỉnh sửa/từ chối hành động nguy hiểm trước khi thực thi; audit log đầy đủ.
* **K6. Multi-Agent & MCP:**
  * *Giỏi:* Phân định rõ vai trò và ranh giới trách nhiệm của từng sub-agent hoặc MCP tool; cơ chế phối hợp (coordination) và tổng hợp kết quả chính xác, có trace giao tiếp.
* **K7. Verification & Evaluation:**
  * *Giỏi:* Có Definition of Done cho từng tác vụ; harness tự động xác thực output bằng parser/linter; bộ benchmark đo lường Precision, Recall, FPR, Latency và Cost qua các phiên bản.
* **K8. Security, Governance & Observability:**
  * *Giỏi:* Áp dụng nguyên tắc quyền tối thiểu (Least Privilege), read-only scope, secret masking; có test case phòng chống Prompt Injection; hệ thống trace trực quan tra cứu được toàn bộ luồng suy luận.

---

## 5. Điều Kiện Bắt Buộc & Điểm Trừ (Penalties)

| Tình huống vi phạm | Hình thức xử lý |
| :--- | :--- |
| **Agent không chạy được trong demo** và không có video/trace dự phòng | Tiêu chí **U1 của các UC liên quan = 0 điểm**. |
| **Tập UC nộp thiếu mảng kiến thức** (theo mục 2.2) | **Trừ 0,5 điểm** Phần II cho mỗi mảng K bị thiếu. |
| **Không có tập eval chạy được bằng script** (HR-06) | Tiêu chí **U3 của mọi UC tối đa mức Yếu**. |
| **Lộ API key, token hoặc mật khẩu trong repo/git history** | **Trừ 1,0 điểm** trên tổng điểm đồ án. |
| **Thiếu `.env.example`** hoặc hướng dẫn cấu hình an toàn | **Trừ 0,25 điểm** trên tổng điểm đồ án. |
| **Tool/skill chạy lệnh nguy hiểm mà không có approval gate** | Tiêu chí **U2 của UC liên quan = 0 điểm**. |
| **Không minh bạch việc dùng AI**, không trích dẫn nguồn | **Trừ 0,5 điểm** tổng; nếu nghiêm trọng xử lý như gian lận. |
| **Vi phạm quy định riêng của đề tài** (dùng agent có sẵn làm hộ như CodeRabbit, Copilot, PR-Agent...) | **0 điểm toàn bộ các UC liên quan**. |
| **Sao chép bài, dùng chung repo, giả mạo commit** | **0 điểm đồ án A4**, chuyển Hội đồng kỷ luật xử lý. |

---

## 6. Đánh Giá Cá Nhân & Hệ Số Vấn Đáp

Vấn đáp kéo dài 15–20 phút mỗi nhóm ($\sim 3-4$ phút mỗi sinh viên). Điểm số cá nhân được tính bằng:
$$\text{Điểm cá nhân} = \text{Điểm nhóm} \times \text{Hệ số vấn đáp}$$

| Mức | Biểu hiện khi vấn đáp | Hệ số |
| :--- | :--- | :---: |
| **Nắm vững** | Giải thích đúng, sâu sắc UC mình sở hữu; trả lời tốt câu hỏi liên quan đến kiến trúc chung và phần của thành viên khác; có commit code rõ ràng. | **1,0** |
| **Nắm được** | Giải thích đúng UC của mình, nhưng còn lúng túng ở phần kiến trúc chung. | **0,8** |
| **Nắm sơ sài** | Chỉ mô tả bề mặt, không giải thích được thiết kế harness hoặc code của UC mình làm. | **0,5** |
| **Không nắm** | Không giải thích được phần việc được giao, hoặc không có đóng góp trên Git repo. | **0,0 – 0,3** |

---

## 7. Quy Trình Chấm 3 Vòng

1. **Vòng 1: Checklist tự động trên GitHub Classroom CI**
   * Kiểm tra tự động các yêu cầu nền HR-01 đến HR-07: Quét secret lộ, chạy test suite, kiểm tra format skill contract, kiểm tra độ phủ K1–K8.
2. **Vòng 2: Đánh giá Video Demo (Tối đa 15 phút)**
   * Chấm tiêu chí U1 (Chức năng) của từng UC và độ hoàn thiện UI/UX của phần mềm.
3. **Vòng 3: Vấn đáp trực tiếp theo ca (15–20 phút)**
   * Trợ giảng và Giảng viên đối chiếu báo cáo, kiểm tra trace thực tế, chấm U2, U3 và xác định hệ số vấn đáp cá nhân của từng thành viên.
