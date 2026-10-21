# SE373 · BUỔI 03: AGENT FUNDAMENTALS — AGENT LOOP, ĐIỀU KIỆN DỪNG VÀ DEBUGGING

> **Tài liệu tham khảo học phần SE373:** Kỹ thuật xây dựng hệ thống Agentic AI (UIT)  
> **Chủ đề:** Cấu trúc Vòng lặp Agent · Mô hình ReAct · 5 Điều kiện dừng · Quy trình Debugging

---

## 1. Định nghĩa và Cấu tạo tối thiểu của AI Agent

- **Định nghĩa:** AI Agent là phần mềm có khả năng tự chủ hoạt động, đưa ra quyết định ở từng bước nhằm đạt được mục tiêu (*Goal*) đã đề ra mà không cần con người can thiệp liên tục.
- **Bốn thành phần tối thiểu của Agent:**
  1. **Goal (Mục tiêu):** Đích đến cụ thể cần hoàn thành (vd: *"Review toàn bộ diff của PR #42 và đưa ra gợi ý sửa lỗi bảo mật"*).
  2. **Tools (Công cụ):** Tập các hàm mà Agent được phép gọi để tác động hoặc lấy dữ liệu từ môi trường.
  3. **Loop (Vòng lặp):** Cơ chế đưa kết quả hành động trở lại làm đầu vào cho lượt suy luận tiếp theo.
  4. **Perception / Observation (Quan sát):** Dữ liệu thu nhận được từ môi trường sau khi thực thi tool.

---

## 2. Sơ đồ trục Vòng lặp Agent & Kiến trúc ReAct

### 2.1. Chu trình lặp cơ bản

```
             ┌──────────────────────────────────────────────┐
             │                USER REQUEST                  │
             └──────────────────────┬───────────────────────┘
                                    ▼
       ┌───────────────────► [ 1. CONTEXT ] (Harness lọc & nén)
       │                            │
       │                            ▼
       │                     [ 2. MODEL ] (Suy luận: Thought + Action)
       │                            │
       │      ┌─────────────────────┴─────────────────────┐
       │      ▼                                           ▼
       │ [Gọi Tool]                                [Không gọi Tool]
       │      │                                           │
       │      ▼                                           ▼
       │ [ 3. HARNESS ]                             [ THÀNH CÔNG ]
       │ (Kiểm tra quyền, chạy Tool)               (Trả kết quả cuối)
       │      │
       │      ▼
       │ [ 4. OBSERVATION ]
       └──────┴─── (Kết quả tool trả về)
```

### 2.2. Mẫu suy luận ReAct (Reasoning + Acting)
- **Chu trình:** $\text{Thought (Suy nghĩ)} \rightarrow \text{Action (Hành động gọi tool)} \rightarrow \text{Observation (Quan sát kết quả)} \rightarrow \text{Thought...}$
- **Vì sao ReAct vượt trội so với Chain-of-Thought thuần túy?**
  - Chain-of-Thought chỉ suy luận dựa trên kiến thức tĩnh có sẵn trong trọng số model $\rightarrow$ rất dễ bịa đặt (hallucination).
  - ReAct liên tục đưa dữ kiện tươi mới từ môi trường thực tế (kết quả chạy test, diff code thật, phản hồi API) vào giữa chuỗi lập luận, giúp model tự điều chỉnh đường đi khi gặp dữ liệu không như kỳ vọng.

---

## 3. Năm Điều Kiện Dừng (Termination Conditions)

Hệ thống Agent **BẮT BUỘC** phải có các cơ chế dừng rõ ràng để không rơi vào tình trạng ngốn vô tận token và ngân sách:

| STT | Tên điều kiện dừng | Kiểu dừng | Cơ chế phát hiện | Hành động của Harness |
| :---: | :--- | :--- | :--- | :--- |
| **1** | **Model thôi gọi Tool** | Bình thường | Model trả về text cuối cùng hoặc structured output hoàn tất mà không phát sinh thêm `tool_calls`. | Harness nghiệm thu kết quả qua lớp Verification rồi trả về cho User. |
| **2** | **Chạm trần ngân sách (Budget Exceeded)** | Bất thường | Harness đếm thấy số vòng vượt quá `max_steps` (vd: > 10 vòng), số token vượt trần, hoặc hết thời gian timeout. | Cưỡng chế ngắt vòng lặp, ghi log cảnh báo, trả về trạng thái partial / failure. |
| **3** | **Phát hiện lặp vô tận (Loop Detected)** | Bất thường | Agent gọi lại cùng một tool với cùng tham số (`tool_name`, `args`) hoặc nhận lại cùng một kết quả lỗi liên tiếp. | Dừng vòng lặp, đánh dấu lỗi suy luận vòng tròn. |
| **4** | **Bế tắc không tiến triển (Stagnation)** | Bất thường | Agent không lặp tool nhưng đổi liên tục các tool khác nhau và tất cả đều thất bại mà không tiến gần tới Goal. | Ngắt vòng lặp, thông báo cần can thiệp. |
| **5** | **Vượt thẩm quyền (Permission Breach)** | Bất thường / Chờ duyệt | Agent định gọi một action nhạy cảm (vd: `git push --force`, `delete_database`, `merge_pr`). | Harness giữ lại action, tạm dừng Agent và kích hoạt **Human Approval (HITL)**. |

---

## 4. Cài đặt Bộ Phát hiện Lặp (LoopDetector) trong Python

```python
import hashlib
import json
from typing import Any, Dict, List

class LoopDetector:
    def __init__(self, max_repeated_actions: int = 2, window_size: int = 5):
        self.max_repeated = max_repeated_actions
        self.window_size = window_size
        self.action_history: List[str] = []

    def _hash_action(self, tool_name: str, args: Dict[str, Any]) -> str:
        serialized = json.dumps({"tool": tool_name, "args": args}, sort_keys=True)
        return hashlib.md5(serialized.encode("utf-8")).hexdigest()

    def check_and_record(self, tool_name: str, args: Dict[str, Any]) -> bool:
        """Trả về True nếu phát hiện bị lặp vô tận (Loop detected)."""
        act_hash = self._hash_action(tool_name, args)
        self.action_history.append(act_hash)
        
        # Chỉ xét trong cửa sổ trượt window_size
        recent_window = self.action_history[-self.window_size:]
        repeated_count = recent_window.count(act_hash)
        
        if repeated_count >= self.max_repeated:
            return True # Đã lặp lại quá số lần cho phép
        return False
```

---

## 5. Quy trình 4 Bước Debug Agent Chuyên nghiệp

Khi Agent chạy sai hoặc không đạt kết quả mong muốn, kỹ sư Agentic AI áp dụng quy trình 4 bước chuẩn mực:

```
[ Bước 1: Tái hiện lỗi ] (Reproduce with deterministic logs/trace)
          │
          ▼
[ Bước 2: Khoanh vùng vòng sai đầu tiên ] (Catch the first divergent turn)
          │
          ▼
[ Bước 3: Sửa lớp Harness ] (Fix Tool schema, Context, Skill or Prompt)
          │
          ▼
[ Bước 4: Kiểm chứng lại ] (Verify on regression eval test cases)
```

1. **Bước 1 - Tái hiện lỗi:** Chạy lại đúng input với bộ seed và config đã ghi nhận trong logs/trace.
2. **Bước 2 - Bắt vòng sai đầu tiên:**  
   > *Nguyên tắc sống còn:* **Không xem kết quả cuối cùng.** Kết quả cuối sai chỉ là hệ quả tích lũy. Phải lật lại trace để tìm chính xác **bước lặp (turn/step) đầu tiên** mà Agent đưa ra quyết định lệch khỏi kỳ vọng.
3. **Bước 3 - Sửa Harness (Thay vì đổi Model):**
   - Nếu Model chọn nhầm tool: Sửa lại mô tả `description` và tham số của tool cho rành mạch hơn.
   - Nếu Model bị thiếu dữ kiện: Điều chỉnh lại `Context / Retrieval Harness`.
   - Nếu Model trả sai format: Ép lại `Structured Output` schema hoặc bổ sung Few-shot ví dụ.
4. **Bước 4 - Kiểm chứng (Evaluation):** Chạy lại test suite để đảm bảo sửa được lỗi đó mà không làm hỏng các test cases cũ đã pass.
