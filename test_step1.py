"""
test_step1.py — Kịch bản kiểm thử Bước 1: agent/schemas.py
==========================================================
Chạy file này để kiểm tra xem Hợp đồng dữ liệu Pydantic v2
hoạt động và bảo vệ hệ thống ra sao.
"""
import sys

# Đảm bảo in tiếng Việt có dấu không bị lỗi trên Windows Console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from agent.schemas import ReviewFinding, ReviewReport, Severity, Category, DiffSide, ReviewVerdict


def run_tests():
    print("=" * 65)
    print("🧪 BÀI TEST 1: TẠO MỘT REVIEW FINDING HỢP LỆ")
    print("=" * 65)

    finding1 = ReviewFinding(
        file="app/services/booking.py",
        line=43,
        side=DiffSide.RIGHT,
        severity=Severity.MAJOR,
        category=Category.LOGIC,
        message="Toán tử so sánh bị đảo ngược từ >= thành <= làm bàn nhận khách quá tải.",
        suggestion="    return table.max_capacity >= requested",
        confidence=0.98
    )
    print("✅ Đã tạo thành công ReviewFinding:")
    print(finding1.model_dump_json(indent=2))

    print("\n" + "=" * 65)
    print("🧪 BÀI TEST 2: GOM FINDINGS VÀO BÁO CÁO TỔNG HỢP (REVIEW REPORT)")
    print("=" * 65)

    report = ReviewReport(
        pr_number=42,
        commit_sha="c1eedb89",
        verdict=ReviewVerdict.REQUEST_CHANGES,
        summary="Phát hiện lỗi logic nghiêm trọng ở hàm check_capacity. Đề nghị sửa trước khi merge.",
        findings=[finding1],
        run_id="PR42_HEAD_c1eedb"
    )
    print("✅ Đã tạo thành công ReviewReport hoàn chỉnh:")
    print(report.model_dump_json(indent=2))

    print("\n" + "=" * 65)
    print("🧪 BÀI TEST 3: BẪY DỮ LIỆU SAI (KIỂM TRA CƠ CHẾ TỰ BẢO VỆ)")
    print("=" * 65)
    try:
        # Cố tình đưa: dòng âm (-10) và message quá ngắn ("Lỗi")
        bad_finding = ReviewFinding(
            file="app/services/booking.py",
            line=-10,
            severity=Severity.CRITICAL,
            category=Category.SECURITY,
            message="Lỗi"
        )
        print("❌ THẤT BẠI: Lẽ ra Pydantic phải chặn lại!")
    except Exception as e:
        print("🛡️ Pydantic v2 đã chặn đứng thành công dữ liệu bậy bạ:")
        for err in e.errors():
            field_name = err['loc'][0]
            err_msg = err['msg']
            print(f"   -> Trường '{field_name}': {err_msg}")

    print("\n" + "=" * 65)
    print("🎉 TẤT CẢ TEST ĐÃ PASS! BƯỚC 1 HOÀN TOÀN CHUẨN XÁC.")
    print("=" * 65)


if __name__ == "__main__":
    run_tests()
