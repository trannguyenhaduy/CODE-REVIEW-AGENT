"""
test_step3.py — Kịch bản kiểm thử Bước 3: agent/harness/validator.py
=====================================================================
Chạy file này để kiểm tra xem lớp Harness Validator kiểm định hàng loạt
findings và tự động chốt phán quyết (Verdict) ra sao.
"""
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from agent.schemas import ReviewFinding, Severity, Category, DiffSide, ReviewVerdict
from agent.tools.git_diff_reader import GitDiffReader
from agent.harness.validator import FindingValidator

# Đoạn diff mẫu chỉ có dòng 43 là dòng mới được thêm vào
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
    print("🧪 BÀI TEST BƯỚC 3: KIỂM ĐỊNH HÀNG LOẠT (FINDING VALIDATOR HARNESS)")
    print("=" * 65)

    # 1. Bóc tách diff trước để có ranh giới dòng
    reader = GitDiffReader()
    parsed_diff = reader.parse(SAMPLE_DIFF)

    # 2. Khởi tạo Validator với diff vừa bóc tách
    validator = FindingValidator(parsed_diff=parsed_diff)

    # 3. Giả lập AI sinh ra 3 finding với các tình huống khác nhau:
    # Finding 1: Chuẩn 100% (Dòng 43, lỗi Major)
    finding_valid = ReviewFinding(
        file="app/services/booking.py",
        line=43,
        side=DiffSide.RIGHT,
        severity=Severity.MAJOR,
        category=Category.LOGIC,
        message="Toán tử so sánh bị đảo ngược từ >= sang <=.",
        suggestion="    return table.max_capacity >= requested"
    )

    # Finding 2: AI nhận xét đúng bản chất nhưng bịa số dòng 999 (ngoài diff)
    finding_out_of_diff = ReviewFinding(
        file="app/services/booking.py",
        line=999,
        side=DiffSide.RIGHT,
        severity=Severity.MINOR,
        category=Category.CONVENTION,
        message="Nên thêm chú thích kiểu trả về cho rõ ràng."
    )

    # Finding 3: AI nhận xét vào một file lạ không hề có trong PR
    finding_wrong_file = ReviewFinding(
        file="app/auth/login.py",
        line=20,
        side=DiffSide.RIGHT,
        severity=Severity.NIT,
        category=Category.OTHER,
        message="Nên đổi tên biến cho dễ hiểu hơn."
    )

    findings_list = [finding_valid, finding_out_of_diff, finding_wrong_file]

    # 4. Chạy hàm kiểm định hàng loạt (validate_batch)
    batch_result = validator.validate_batch(findings_list)

    print(f"📊 Kết quả kiểm định {batch_result.total_input} findings:")
    print(f"   • Hợp lệ được đăng inline (valid): {len(batch_result.valid)}")
    print(f"   • Chuyển thành comment cấp PR (pr_level): {len(batch_result.pr_level_comments)}")
    print(f"   • Vi phạm bị loại bỏ (invalid): {len(batch_result.invalid)}")
    print(f"   • Tỷ lệ đạt chuẩn (pass_rate): {batch_result.pass_rate:.1%}")

    print("\n🔍 Chi tiết từng loại:")
    for f in batch_result.valid:
        print(f"   ✅ [INLINE] {f.file}:{f.line} ({f.severity.upper()}) -> {f.message[:40]}...")

    for f in batch_result.pr_level_comments:
        print(f"   🔄 [PR-LEVEL COMMENT] {f.file}:{f.line} -> Chuyển lên đầu PR vì dòng ngoài diff")

    # 5. Kiểm tra hàm tự động ra phán quyết (determine_verdict)
    verdict = validator.determine_verdict(batch_result.valid)
    print("\n" + "=" * 65)
    print("⚖️ TỰ ĐỘNG CHỐT PHÁN QUYẾT CHO TOÀN BỘ PR:")
    print("=" * 65)
    print(f"👉 Phán quyết của Agent: {verdict.value.upper()} (Chặn merge PR do có lỗi MAJOR)")

    assert verdict == ReviewVerdict.REQUEST_CHANGES, "Lỗi: Đáng lẽ phải REQUEST_CHANGES!"
    print("\n🎉 BƯỚC 3 ĐÃ HOÀN TOÀN THÀNH CÔNG VÀ ĐẠT CHUẨN RUBRIC!")
    print("=" * 65)


if __name__ == "__main__":
    run_tests()
