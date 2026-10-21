# SE373 · BUỔI 01: TỔNG QUAN LLM VÀ AGENTIC AI — 12 LỚP HARNESS

> **Tài liệu tham khảo học phần SE373:** Kỹ thuật xây dựng hệ thống Agentic AI (UIT)  
> **Giảng viên lý thuyết:** TS. Đỗ Trọng Hợp, ThS. Ngô Ngọc Đăng Khoa, ThS. Phạm Hoàng Hải

---

## 1. Nền tảng: Cơ chế hoạt động của LLM

- **Bản đồ khái niệm:**
  ```
  [ Trí tuệ Nhân tạo (AI) ]
       └── [ AI Tạo sinh (GenAI) ]
                └── [ Mô hình Ngôn ngữ Lớn (LLM) ]
  ```
- **Cơ chế lõi:** Dự đoán từ tiếp theo (*Next-token prediction*).
  $$\text{Input: Context} \xrightarrow{\text{Softmax probabilities}} \text{Next Token}$$
  - LLM bản chất là mô hình xác suất thống kê học qua hàng tỷ văn bản.
  - LLM tự thân **không có khả năng tư duy logic đảm bảo**, **không có bộ nhớ trạng thái liên tục**, và **không thể tự thực thi hành động ra thế giới thực** nếu không có phần mềm bao bọc.

---

## 2. Bốn nấc tiến hoá của ứng dụng AI

| Nấc tiến hóa | Đặc điểm kỹ thuật | Khả năng trao quyền cho Model | Ví dụ |
| :--- | :--- | :--- | :--- |
| **1. Completion** | Chuỗi vào $\rightarrow$ chuỗi ra. Model đóng vai trò như một hàm toán học thuần túy (`f(text) -> text`). Không giữ trạng thái. | Cực thấp | Tóm tắt đoạn văn bản, dịch câu đơn lẻ. |
| **2. Chatbot** | Duy trì lịch sử trò chuyện (`chat_history`) qua nhiều lượt hội thoại. | Thấp | ChatGPT cơ bản, hỏi đáp tư vấn sản phẩm. |
| **3. Tool Use (Function Calling)** | Model nhận diện ý định và trả về structured data để ứng dụng gọi API/hàm bên ngoài. | Trung bình | Bot tra cứu thời tiết, bot truy vấn SQL từ câu tự nhiên. |
| **4. Agent** | Vòng lặp tự chủ (*Autonomous loop*): Tự quan sát môi trường, tự lập luận, tự chọn công cụ, tự đánh giá kết quả và quyết định bước tiếp theo cho đến khi đạt mục tiêu. | Cao | Coding agent sửa bug, Code Review agent duyệt PR tự động. |

---

## 3. Ba tiêu chí phân biệt: Chatbot · RAG · Workflow · Agent

Để xác định một hệ thống có phải là Agentic hay không, dùng **3 câu hỏi ranh giới**:
1. **Ai chọn bước tiếp theo?**
2. **Ai giữ trạng thái (State)?**
3. **Ai quyết định khi nào dừng vòng lặp?**

| Loại hình ứng dụng | Ai chọn bước tiếp theo? | Ai giữ trạng thái? | Ai quyết định dừng? | Bản chất cốt lõi |
| :--- | :--- | :--- | :--- | :--- |
| **Chatbot** | Người dùng (qua mỗi lượt prompt) | Hệ thống lưu mảng tin nhắn | Người dùng (ngừng chat) | Hội thoại thụ động, không có hành động can thiệp hệ thống. |
| **RAG Application** | Code quy định cố định (Search $\rightarrow$ Prompt $\rightarrow$ Generate) | Không có trạng thái phức tạp | Code chạy hết pipeline thì dừng | Mở rộng tri thức tĩnh, model không có quyền rẽ nhánh đường đi. |
| **Workflow Automation** | Code định sẵn (if/else, DAG, state machine) | Database / Biến chương trình | Code đạt điều kiện dừng được lập trình trước | *"Engines run workflows"*: Luồng cố định, đáng tin cậy cao cho tác vụ tuyến tính. |
| **AI Agent** | **Chính Model tự suy luận và chọn** | Harness quản lý qua State/Memory | **Model tự dừng** hoặc **Harness can thiệp ngắt** | *"Agents manage workflows"*: Giải quyết bài toán mở, không thể xác định trước đường đi. |

> **Nguyên tắc thiết kế vàng:**  
> Agent đắt hơn về token, độ trễ và khó kiểm thử hơn workflow thông thường. **Chỉ dùng Agent khi bài toán tuyệt đối không thể xác định trước các bước thực hiện từ đầu.**

---

## 4. Công thức cốt lõi: $\text{Agent} = \text{Model} + \text{Harness}$

> *"Agent = Model + Harness. If you're not the model, you're the harness."*  
> *"A decent model with a great harness beats a great model with a bad harness."*

- **Model:** Cung cấp **năng lực** (khả năng hiểu ngôn ngữ, suy luận xác suất, sinh nội dung).
- **Harness:** Cung cấp **độ tin cậy** (toàn bộ cơ chế phần mềm bao bọc quanh model để biến năng lực ngôn ngữ thành hành vi an toàn, chuẩn xác trên hệ thống thật).

---

## 5. 12 Lớp Harness bảo vệ và điều phối Agent

12 lớp Harness được chia thành 3 nhóm chức năng then chốt:

```
                          ┌────────────────────────────────┐
                          │         12 LỚP HARNESS         │
                          └────────────────┬───────────────┘
          ┌────────────────────────────────┼────────────────────────────────┐
          ▼                                ▼                                ▼
[ Nhóm Tri thức & Năng lực ]     [ Nhóm Trạng thái & Quy trình ]     [ Nhóm An toàn & Giám sát ]
  1. Context                       5. Memory                           9. Permission
  2. Tools                         6. State                           10. Logging
  3. Skills                        7. Workflow                        11. Human Approval
  4. Retrieval                     8. Verification                    12. Handoff
```

### Nhóm 1: Tri thức và Khả năng hành động
1. **Context Harness:** Quyết định chính xác dữ liệu nào được đưa vào context window tại mỗi bước. Chặn tình trạng context bị loãng, hallucination, và chi phí token tăng vọt.
2. **Tools Harness:** Định nghĩa tập hàm agent được phép gọi, kèm JSON Schema chuẩn và mô tả rõ ràng. Chặn việc agent bất lực (không có tool) hoặc phá hoại (gọi hàm ngoài thẩm quyền).
3. **Skills Harness:** Gói chỉ dẫn quy trình có tính module hóa và tái sử dụng cao (`SKILL.md`). Đảm bảo tính nhất quán khi xử lý cùng một nghiệp vụ chuyên môn.
4. **Retrieval Harness (RAG):** Truy xuất tri thức động từ bên ngoài (Vector DB, Knowledge Base, Git repo). Cung cấp dẫn chứng chính xác và trích dẫn nguồn.

### Nhóm 2: Trạng thái và Quy trình
5. **Memory Harness:** Quản lý dữ liệu lưu giữ trong phiên (Short-term) và giữa các phiên (Long-term). Chặn việc agent hỏi lại thông tin đã biết hoặc nhớ thông tin vi phạm chính sách bảo mật.
6. **State Harness:** Quản lý trạng thái tác vụ hiện tại (đang ở bước nào, đã thực thi action nào, kết quả ra sao). Giúp agent có thể dừng, phục hồi (checkpoint/resume) mà không mất tiến trình.
7. **Workflow Harness (vd: LangGraph):** Cấu trúc hóa các luồng phức tạp dưới dạng đồ thị (Nodes, Edges, Conditional branching, Sub-graphs). Giữ agent đi đúng quỹ đạo nghiệp vụ.
8. **Verification Harness:** Kiểm tra, thẩm định kết quả đầu ra trước khi trả về cho user hoặc chuyển sang bước kế tiếp (schema validation, code linting, regression testing).

### Nhóm 3: An toàn, Con người và Giám sát
9. **Permission Harness:** Phân quyền và cô lập tài nguyên mà agent được phép tác động (chặn SQL injection, chặn xóa nhầm database, chặn ghi đè branch main).
10. **Logging & Observability Harness:** Ghi vết chi tiết từng token, prompt, response, tool call, latency, cost và step decision. Giúp debug và loại bỏ rủi ro tin vào lời agent tự biện minh.
11. **Human Approval Harness (HITL):** Điểm dừng an toàn bắt buộc có sự can thiệp và phê duyệt của con người trước khi thực hiện các hành động nguy hiểm/nhạy cảm (vd: deploy production, xóa code, merge PR).
12. **Handoff Harness:** Cơ chế chuyển giao nhiệm vụ mượt mà giữa Agent $\leftrightarrow$ Agent hoặc từ Agent $\rightarrow$ Nhân viên con người khi gặp tình huống ngoài khả năng.

---

## 6. Case Studies: Phân tích 3 sự cố thất bại thực tế (Thiếu Harness)

| Sự cố | Diễn biến thực tế | Lỗi do Model hay do Harness? | Lớp Harness bị thiếu | Cơ chế khắc phục chuẩn |
| :--- | :--- | :--- | :--- | :--- |
| **Cursor Bot (04/2025)** | Bot hỗ trợ tự bịa ra chính sách: *"Mỗi tài khoản chỉ dùng trên 1 thiết bị"*, khiến khách hàng hoang mang và hủy gói dịch vụ. | Model không lỗi (nó chỉ sinh câu văn nghe hợp lý). Lỗi ở Harness! | `Retrieval`, `Verification`, `Human Approval` | Bắt buộc mọi câu trả lời về policy phải có trích dẫn tài liệu chính thức (`Retrieval`); kiểm tra trích dẫn (`Verification`); nếu không có tài liệu thì từ chối phát ngôn. |
| **Air Canada (02/2024)** | Chatbot bịa ra chính sách giảm giá vé tang lễ hồi tố. Hãng hàng không bị tòa án phạt thua kiện. | Model sinh theo xác suất. Lỗi ở Harness thiếu kiểm chứng. | `Retrieval`, `Verification`, `Logging` | Bắt buộc trích dẫn văn bản quy định; ghi vết audit log đầy đủ; cơ chế verify chặn các cam kết tài chính trái phép. |
| **GitHub MCP (05/2025)** | Agent được cấp quyền quá rộng qua MCP, xóa nhầm branch và commit quan trọng trên production repo. | Model thực hiện lệnh theo prompt injection / sai lệch context. | `Permission`, `Human Approval` | Thiết lập quyền Read-only mặc định; các lệnh Write/Delete nguy hiểm bắt buộc qua cơ chế `Human Approval`. |
