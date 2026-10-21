# SE373 · BUỔI 02: CÁC NGUYÊN LÝ CƠ BẢN CỦA LLM-POWERED APP & TOOL USE

> **Tài liệu tham khảo học phần SE373:** Kỹ thuật xây dựng hệ thống Agentic AI (UIT)  
> **Chủ đề:** Prompt & Context Engineering · Structured Output · Function Calling & Tool Use

---

## 1. Định nghĩa LLM-Powered Application

- **LLM-Powered App** là phần mềm gọi mô hình ngôn ngữ lớn (LLM) để xử lý dữ liệu đầu vào và đưa kết quả (output) trực tiếp vào luồng xử lý nghiệp vụ của ứng dụng (thay vì chỉ hiển thị đoạn chat cho con người đọc).
- **Ví dụ điển hình - Issue Triage App:**
  - *Input:* Người dùng nhập mô tả lỗi (*"Nút thanh toán Momo bị đơ trên iOS"*).
  - *Mục tiêu:* Phân loại component (`payment`), mức độ nghiêm trọng (`P1 - Critical`), gán team phụ trách (`mobile-team`).
  - *Vấn đề nếu dùng văn bản tự do:* Model trả lời dông dài (*"Tôi nghĩ vấn đề này thuộc về..."*), code `if/else` không thể parse được và sẽ crash khi deploy.

---

## 2. Token, Context Window và Context Engineering

### 2.1. Token & Context Window
- LLM không đọc ký tự hay từ nguyên vẹn mà đọc qua đơn vị **Token** (khoảng 0.75 từ tiếng Anh, hoặc 1–2 ký tự tiếng Việt có dấu).
- **Context Window:** Kích thước tối đa mô hình có thể tiếp nhận trong một lượt gọi (bao gồm System Prompt + Chat History + Input + Output).
- **Hiện tượng "Lost in the Middle":** Khi đưa quá nhiều dữ liệu vào context window, mô hình thường nhớ tốt phần đầu và phần cuối, nhưng bỏ quên thông tin quan trọng ở giữa.

### 2.2. Prompt Engineering vs Context Engineering

| Khái niệm | Phạm vi tiếp cận | Bản chất công việc |
| :--- | :--- | :--- |
| **Prompt Engineering** | Từng prompt đơn lẻ | Tinh chỉnh câu từ, vai trò (*system persona*), chỉ dẫn (*instructions*) để model hiểu rõ mục tiêu. |
| **Context Engineering** | Toàn bộ vòng đời ứng dụng | **Chiến lược dữ liệu tại runtime:** Chọn lọc thông tin gì cần đưa vào, cắt tỉa thông tin thừa, nén lịch sử, tổ chức thứ tự dữ liệu nhằm tối ưu độ chính xác và chi phí token. |

---

## 3. In-Context Learning & Few-Shot Prompting

- **In-Context Learning:** Khả năng LLM học cách giải quyết một nhiệm vụ mới ngay trong ngữ cảnh cung cấp mà **KHÔNG hề cập nhật bất kỳ trọng số (weights) nào của mô hình**.
- **Kỹ thuật Few-Shot:** Đưa kèm một vài cặp mẫu `(Input, Output)` vào prompt để định hình phong cách và định dạng phản hồi.

### Đánh đổi (Trade-offs) của Few-Shot:
- **Ưu điểm:** Cực kỳ hiệu quả cho các bài toán phân loại theo quy ước riêng của doanh nghiệp hoặc định dạng phức tạp.
- **Nhược điểm & Rủi ro:**
  - Tốn thêm token chi phí trên mỗi lượt gọi API.
  - Có thể gây **bias**: Mô hình có xu hướng bắt chước y hệt giá trị hoặc phong cách của các ví dụ mẫu thay vì tổng quát hóa dữ liệu mới.

---

## 4. Structured Output với Pydantic

Để phần mềm có thể tương tác an toàn với LLM, kết quả trả về từ model **bắt buộc phải có cấu trúc chặt chẽ (Structured Output)**, tuân thủ JSON Schema được xác thực tại runtime.

### Cài đặt với Pydantic v2 trong Python:

```python
from typing import Literal, List, Optional
from pydantic import BaseModel, Field

class CodeIssue(BaseModel):
    file_path: str = Field(description="Đường dẫn tương đối tới file có lỗi")
    line_number: int = Field(description="Dòng code xảy ra lỗi hoặc cần chỉnh sửa")
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "NITPICK"] = Field(
        description="Mức độ nghiêm trọng của vấn đề"
    )
    category: Literal["SECURITY", "PERFORMANCE", "BUG", "STYLE", "TEST"] = Field(
        description="Danh mục lỗi"
    )
    issue_description: str = Field(description="Mô tả chi tiết nguyên nhân lỗi")
    suggested_fix: Optional[str] = Field(
        default=None, 
        description="Đoạn code sửa đổi gợi ý (chuẩn markdown suggestion block)"
    )

class PullRequestReviewResult(BaseModel):
    summary: str = Field(description="Tóm tắt tổng quan về chất lượng của PR")
    overall_status: Literal["APPROVE", "REQUEST_CHANGES", "COMMENT"] = Field(
        description="Quyết định review của agent"
    )
    issues: List[CodeIssue] = Field(default_factory=list, description="Danh sách các vấn đề phát hiện")
```

### Lợi ích cốt lõi của Pydantic & Structured Output:
1. **Contract an toàn:** Đảm bảo kiểu dữ liệu (`int`, `str`, `List`, `Literal`) đúng 100%.
2. **Runtime Validation:** Nếu model trả sai field hoặc thiếu enum, Pydantic ném `ValidationError`, cho phép Harness bắt lỗi và yêu cầu model sửa lại ngay lập tức (Self-healing / Retry).
3. **IDE Autocomplete:** Developer làm việc với các object có định kiểu mạnh, tránh bug ngớ ngẩn do gõ sai tên thuộc tính.

---

## 5. Function Calling & Tool Use

### 5.1. Phân biệt Structured Output và Function Calling

```
┌────────────────────────────────────────────────────────────────────────┐
│ Structured Output:                                                     │
│ Model ──[Sinh JSON hợp lệ]──> Hệ thống nhận dữ liệu để kết thúc/lưu    │
└────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────┐
│ Function Calling (Tool Use):                                           │
│ Model ──[Yêu cầu gọi hàm + args]──> Harness thực thi ──[Observation]──>│
│ └── Model tiếp tục suy luận và quyết định bước tiếp theo...            │
└────────────────────────────────────────────────────────────────────────┘
```

- **Ai thực thi hàm trong Function Calling?**
  - **CHÍNH LÀ PHẦN MỀM / HARNESS CỦA BẠN THỰC THI**, **LLM hoàn toàn KHÔNG tự thực thi hàm**.
  - LLM chỉ đóng vai trò phân tích ý định và trích xuất đúng tên hàm cùng các tham số JSON.

### 5.2. Vòng đời 5 bước của Tool Use

```
User Input
    │
    ▼
[ 1. Gửi System Prompt + Tools Definition (JSON Schema) ]
    │
    ▼
[ 2. LLM phản hồi: tool_calls=[name, arguments] ]
    │
    ▼
[ 3. Harness kiểm tra quyền & Thực thi hàm cục bộ ] (vd: git diff, run test)
    │
    ▼
[ 4. Harness đưa Tool Output (Observation) ngược lại context ]
    │
    ▼
[ 5. LLM đọc Observation: quyết định gọi tiếp tool khác HOẶC trả lời cuối cùng ]
```
