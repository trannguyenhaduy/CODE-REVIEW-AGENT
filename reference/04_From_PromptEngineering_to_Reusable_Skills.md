# SE373 · BUỔI 04: TỪ PROMPT ENGINEERING ĐẾN REUSABLE SKILLS — CHUẨN THIẾT KẾ SKILL.MD

> **Tài liệu tham khảo học phần SE373:** Kỹ thuật xây dựng hệ thống Agentic AI (UIT)  
> **Giảng viên:** ThS. Ngô Ngọc Đăng Khoa  
> **Chủ đề:** Khái niệm Agent Skill · Cấu trúc thư mục Skill · Quy chuẩn viết SKILL.md · 5 Anti-patterns

---

## 1. Bản chất: Từ Chatbot đến Reusable Agent Skill

- **Sự khác biệt cốt lõi:**
  - *Chatbot:* Người dùng hỏi $\rightarrow$ nhận text trả lời $\rightarrow$ người dùng tự copy ra ngoài xử lý thủ công.
  - *Agent Skill:* Gói chỉ dẫn quy trình có tính **module hóa**, **tái sử dụng cao** và **kiểm chứng được**, giúp Agent tự động hoàn thành một nhiệm vụ nghiệp vụ trọn vẹn từ đầu đến cuối.
- **Vai trò của Skill trong kiến trúc Harness:**
  - Skill chuẩn hóa cách thức giải quyết một bài toán lặp đi lặp lại.
  - Giúp agent thực thi ổn định, nhất quán, không bị phụ thuộc vào sự ngẫu hứng của prompt tự do.

---

## 2. Cấu trúc thư mục tiêu chuẩn của một Skill

Một Skill chuẩn trong hệ sinh thái Agentic gồm 4 thành phần được tổ chức khoa học:

```
skills/<tên-skill>/
├── SKILL.md              # [Bắt buộc] Hướng dẫn tổng quan, trigger, workflow 5-8 bước
├── references/           # [Tài liệu cho LLM] Quy tắc nghiệp vụ, tiêu chí chất lượng, schema
├── scripts/              # [Code cho Machine] Script kiểm tra JSON, đếm số lượng, lint code
└── examples/             # [Ví dụ mẫu] Mẫu input/output chuẩn để LLM tham chiếu (Few-shot)
```

| Thành phần | Đối tượng tiêu thụ | Nội dung chứa đựng | Mục đích sử dụng |
| :--- | :--- | :--- | :--- |
| **`SKILL.md`** | Agent & Developer | Frontmatter YAML + Workflow tóm lược 5–8 bước | Bản đồ chỉ đường tổng thể, agent đọc khi được kích hoạt. |
| **`references/`** | **LLM (Suy luận)** | Checklist chuyên sâu, quy tắc đánh giá, rubric chấm điểm, format output chi tiết | Chứa những thứ cần tư duy, cân nhắc, diễn đạt ngữ nghĩa. |
| **`scripts/`** | **Machine (Chính xác)** | Code Python/Bash: validate JSON schema, đếm số mục, lint cú pháp, check regex | Thực hiện các tác vụ máy tính làm tốt hơn LLM: đếm, so khớp, kiểm thử. |
| **`examples/`** | LLM | Cặp dữ liệu mẫu `(input_diff, output_review.json)` | Cung cấp mẫu đối sánh chuẩn mực cho in-context learning. |

---

## 3. Tiêu chuẩn vàng khi thiết kế `SKILL.md`

### 3.1. Cấu trúc Frontmatter YAML
Phần frontmatter là **nội dung duy nhất mà agent luôn đọc ngay cả khi chưa load toàn bộ nội dung skill**, do đó phải viết cực kỳ chính xác:

```yaml
---
name: pr-code-review
description: Tự động phân tích git diff của Pull Request, phân loại lỗi theo mức độ (severity) và danh mục (security, performance, logic, style), đồng thời tạo gợi ý sửa trực tiếp dạng github suggestion block. Dùng khi nhận được webhook PR mới hoặc lệnh review từ developer. KHÔNG dùng để commit trực tiếp hoặc tự ý merge PR.
allowed-tools: GitDiffReader, ASTParser, SyntaxLinter, SecurityScanner, PostCommentTool
---
```

> **Nguyên tắc viết Description (Trigger):**  
> Nêu rõ **KHI NÀO kích hoạt**, **DÙNG ĐỂ LÀM GÌ**, và đặc biệt phải ghi rõ **KHÔNG DÙNG CHO VIỆC GÌ** để tránh bị agent kích hoạt nhầm.

### 3.2. Tiêu chuẩn viết phần nội dung Workflow trong `SKILL.md`
1. **Độ dài ngắn gọn:** Giữ `SKILL.md` dưới **200 dòng** — mọi chi tiết rườm rà bắt buộc đẩy sang thư mục `references/`.
2. **Quy tắc 5–8 bước:** Workflow chỉ nên gói gọn trong khoảng **5 đến 8 bước**.
3. **Mỗi bước một dòng:** Bắt đầu bằng **động từ hành động** dứt khoát.
4. **Tham chiếu tài liệu:** Trỏ đường dẫn tới file chi tiết trong `references/` thay vì copy nội dung vào `SKILL.md`.
5. **Bước cuối bắt buộc là Verification:** Luôn có bước chạy script kiểm tra tính hợp lệ trước khi công bố hoàn thành.

---

## 4. Phân định ranh giới: LLM vs Machine

| Tác vụ | Phân bổ vào đâu? | Lý do kỹ thuật |
| :--- | :--- | :--- |
| Đánh giá code có tiềm ẩn rủi ro logic hay không | `references/` $\rightarrow$ **LLM** | Cần khả năng hiểu ngữ nghĩa, suy luận nghiệp vụ. |
| Kiểm tra đoạn JSON có đủ 5 trường bắt buộc hay không | `scripts/` $\rightarrow$ **Machine** | LLM đếm hay sót; máy tính chạy `jsonschema.validate()` chỉ mất 1ms và chuẩn xác 100%. |
| Đề xuất cách tái cấu trúc code theo SOLID | `references/` $\rightarrow$ **LLM** | Đòi hỏi tư duy thiết kế phần mềm linh hoạt. |
| Kiểm tra xem dòng code được comment có tồn tại trong diff không | `scripts/` $\rightarrow$ **Machine** | Thao tác so khớp chuỗi/dòng số học thuần túy. |

---

## 5. Năm Lỗi Thường Gặp (Anti-patterns) Cần Tuyệt Đối Tránh

| STT | Tên Anti-pattern | Hậu quả thực tế | Cách khắc phục chuẩn |
| :---: | :--- | :--- | :--- |
| **1** | **`SKILL.md` khổng lồ** | Tốn context window, gây nhiễu và làm model bỏ quên các chỉ dẫn cốt lõi. | Cắt tỉa dưới 200 dòng. Tách quy tắc sang `references/`. |
| **2** | **Description mơ hồ** | Agent tự kích hoạt lung tung hoặc không bao giờ chịu kích hoạt khi cần. | Viết rõ trigger, phạm vi sử dụng và điều kiện cấm kích hoạt. |
| **3** | **Skill ôm đồm đa nhiệm** | Một skill vừa review, vừa viết unit test, vừa deploy $\rightarrow$ khó verify và debug. | Chia nhỏ thành các skill độc lập, kết hợp qua workflow/agent. |
| **4** | **Bắt LLM làm việc của Machine** | Bắt LLM đếm số lượng lỗi, kiểm tra định dạng regex $\rightarrow$ tốn token và hay sinh ảo giác. | Viết script Python trong `scripts/` để máy kiểm tra tự động. |
| **5** | **Thiếu bước kiểm tra (No Verification)** | Agent trả về kết quả lỗi syntax, thiếu trường hoặc sai format mà không biết. | Bước cuối của workflow luôn gọi script verify, chỉ trả kết quả khi test pass. |
