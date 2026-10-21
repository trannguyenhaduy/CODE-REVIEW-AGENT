#!/usr/bin/env python3
"""
Script tính toán tiến độ đồ án SE373 tự động dựa trên các checkbox trong TIEN_DO_DO_AN.md
Tự động đếm [x] và [ ], tính phần trăm %, cập nhật thanh tiến độ và bảng tổng hợp.
"""

import re
import os
import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

TRACKER_FILE = "TIEN_DO_DO_AN.md"

def generate_progress_bar(percentage: float, length: int = 25) -> str:
    filled_len = int(round(length * percentage / 100))
    bar = "█" * filled_len + "░" * (length - filled_len)
    return f"[{bar}] {percentage:.1f}%"

def update_progress():
    if not os.path.exists(TRACKER_FILE):
        print(f"Lỗi: Không tìm thấy file {TRACKER_FILE}")
        sys.exit(1)

    with open(TRACKER_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # Tách các section
    sections = {
        "Phase 0 (Khởi tạo & Nền tảng)": r"### Giai đoạn 0:.*?(?=### Giai đoạn 1:)",
        "Phase 1 (Bootstrap dự án)": r"### Giai đoạn 1:.*?(?=### Giai đoạn 2:)",
        "Phase 2 (Mở rộng năng lực)": r"### Giai đoạn 2:.*?(?=### Giai đoạn 3:)",
        "Phase 3 (Hoàn thiện & Nộp)": r"### Giai đoạn 3:.*?(?=\n## 3\.|\Z)"
    }

    stats = {}
    total_completed = 0
    total_tasks = 0

    for name, pattern in sections.items():
        match = re.search(pattern, content, re.DOTALL)
        if match:
            sec_text = match.group(0)
            completed = len(re.findall(r"-\s*\[x\]", sec_text, re.IGNORECASE))
            pending = len(re.findall(r"-\s*\[ \]", sec_text))
            total = completed + pending
            pct = (completed / total * 100) if total > 0 else 0.0
            stats[name] = {"completed": completed, "total": total, "pct": pct}
            total_completed += completed
            total_tasks += total
        else:
            stats[name] = {"completed": 0, "total": 0, "pct": 0.0}

    overall_pct = (total_completed / total_tasks * 100) if total_tasks > 0 else 0.0
    overall_bar = generate_progress_bar(overall_pct, 25)

    # Tạo bảng markdown tổng kết
    summary_block = f"""<!-- PROGRESS_SUMMARY_START -->
### 📊 Tổng quan Tiến độ Hiện tại: **{overall_pct:.1f}%**
```text
{overall_bar} ({total_completed}/{total_tasks} công việc hoàn thành)
```

| Giai đoạn | Đã xong / Tổng số | Tiến độ | Trạng thái |
| :--- | :---: | :---: | :--- |
| **Giai đoạn 0: Khởi tạo & Nền tảng** | {stats['Phase 0 (Khởi tạo & Nền tảng)']['completed']}/{stats['Phase 0 (Khởi tạo & Nền tảng)']['total']} | **{stats['Phase 0 (Khởi tạo & Nền tảng)']['pct']:.1f}%** | {'✅ Hoàn thành' if stats['Phase 0 (Khởi tạo & Nền tảng)']['pct'] == 100 else '🔄 Đang làm'} |
| **Phase 1: Bootstrap dự án (Tuần 5–7)** | {stats['Phase 1 (Bootstrap dự án)']['completed']}/{stats['Phase 1 (Bootstrap dự án)']['total']} | **{stats['Phase 1 (Bootstrap dự án)']['pct']:.1f}%** | {'✅ Hoàn thành' if stats['Phase 1 (Bootstrap dự án)']['pct'] == 100 else '🔄 Đang thực hiện'} |
| **Phase 2: Mở rộng năng lực (Tuần 8–9)** | {stats['Phase 2 (Mở rộng năng lực)']['completed']}/{stats['Phase 2 (Mở rộng năng lực)']['total']} | **{stats['Phase 2 (Mở rộng năng lực)']['pct']:.1f}%** | {'✅ Hoàn thành' if stats['Phase 2 (Mở rộng năng lực)']['pct'] == 100 else '⏳ Chờ thực hiện'} |
| **Phase 3: Hoàn thiện & Nộp (Tuần 10–12)** | {stats['Phase 3 (Hoàn thiện & Nộp)']['completed']}/{stats['Phase 3 (Hoàn thiện & Nộp)']['total']} | **{stats['Phase 3 (Hoàn thiện & Nộp)']['pct']:.1f}%** | {'✅ Hoàn thành' if stats['Phase 3 (Hoàn thiện & Nộp)']['pct'] == 100 else '⏳ Chờ thực hiện'} |
| **TỔNG CỘNG TOÀN DỰ ÁN** | **{total_completed}/{total_tasks}** | **{overall_pct:.1f}%** | **{'🏆 HOÀN TẤT' if overall_pct == 100 else '🚀 ĐANG TRIỂN KHAI'}** |
<!-- PROGRESS_SUMMARY_END -->"""

    # Thay thế block summary cũ
    new_content = re.sub(
        r"<!-- PROGRESS_SUMMARY_START -->.*?<!-- PROGRESS_SUMMARY_END -->",
        summary_block,
        content,
        flags=re.DOTALL
    )

    with open(TRACKER_FILE, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"Cập nhật thành công! Tổng tiến độ: {overall_pct:.1f}% ({total_completed}/{total_tasks} tasks)")

if __name__ == "__main__":
    update_progress()
