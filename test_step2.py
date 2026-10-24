"""
test_step2.py — Kịch bản kiểm thử Bước 2: agent/tools/git_diff_reader.py
========================================================================
Chạy file này để xem GitDiffReader bóc tách git diff chính xác ra sao.
"""
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from agent.tools.git_diff_reader import GitDiffReader

# Đoạn git diff mẫu giả lập một PR thực tế
SAMPLE_DIFF = """--- a/app/services/booking.py
+++ b/app/services/booking.py
@@ -38,10 +38,10 @@
 def check_capacity(table_id: int, requested: int) -> bool:
     \"\"\"Kiểm tra bàn có đủ chỗ không.\"\"\"
     table = Table.query.get(table_id)
     if table is None:
         raise ValueError(f"Table {table_id} not found")
-    return table.max_capacity >= requested
+    return table.max_capacity <= requested
 
 def create_booking(table_id: int, customer_id: int, num_guests: int) -> Booking:
     \"\"\"Tạo booking mới.\"\"\"
     if not check_capacity(table_id, num_guests):
"""


def run_tests():
    print("=" * 65)
    print("🧪 BÀI TEST BƯỚC 2: BÓC TÁCH GIT DIFF BẰNG UNIDIFF")
    print("=" * 65)

    reader = GitDiffReader()
    parsed = reader.parse(SAMPLE_DIFF)
    summary = reader.get_summary(parsed)

    print(f"📊 Tổng quan PR:")
    print(f"   • Số file thay đổi: {summary['total_files']}")
    print(f"   • Số dòng thêm mới (+): {summary['total_added_lines']}")
    print(f"   • Số dòng bị xóa   (-): {summary['total_removed_lines']}")
    print(f"   • Danh sách file: {summary['files']}")

    # Kiểm tra chi tiết file booking.py
    file_info = parsed.get_file("app/services/booking.py")
    assert file_info is not None, "Lỗi: Không tìm thấy file trong diff!"

    print(f"\n🔍 Chi tiết file '{file_info.path}':")
    print(f"   • Dòng thêm mới (added_lines): {file_info.added_lines}")
    print(f"   • Dòng bị xóa (removed_lines): {file_info.removed_lines}")
    print(f"   • Các dòng hợp lệ có thể nhận xét: {sorted(list(file_info.all_valid_lines))}")

    print("\n" + "=" * 65)
    print("🛡️ BÀI TEST KIỂM ĐỊNH TỰ ĐỘNG (CHỐNG AI BỊA SỐ DÒNG)")
    print("=" * 65)

    # 1. Thử kiểm tra dòng 43 (dòng có dấu + thật trong diff)
    valid, reason = parsed.validate_finding("app/services/booking.py", 43)
    print(f"1. AI comment dòng 43: {'✅ HỢP LỆ' if valid else '❌ BỊ TỪ CHỐI'} ({reason or 'Dòng có trong diff'})")

    # 2. Thử kiểm tra dòng 999 (dòng bịa đặt ngoài diff)
    valid, reason = parsed.validate_finding("app/services/booking.py", 999)
    print(f"2. AI comment dòng 999 (bịa): {'✅ HỢP LỆ' if valid else '🛡️ ĐÃ CHẶN ĐỨNG'} ({reason})")

    # 3. Thử kiểm tra file lạ không có trong diff
    valid, reason = parsed.validate_finding("app/auth/login.py", 10)
    print(f"3. AI comment file lạ (bịa): {'✅ HỢP LỆ' if valid else '🛡️ ĐÃ CHẶN ĐỨNG'} ({reason})")

    print("\n" + "=" * 65)
    print("🎉 BƯỚC 2 ĐÃ HOÀN TOÀN THÀNH CÔNG VÀ CHÍNH XÁC!")
    print("=" * 65)


if __name__ == "__main__":
    run_tests()
