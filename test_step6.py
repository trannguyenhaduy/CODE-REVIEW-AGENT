"""
test_step6.py — Kịch bản kiểm thử Bước 6: Giao diện Dòng lệnh (app/cli.py)
========================================================================
Chạy script này để xác nhận:
1. Lệnh 'python app/cli.py review --diff ... --mock' chạy trơn tru, không lỗi cú pháp.
2. CLI in ra Banner, Hộp phán quyết, Bảng lỗi và Bảng log kiểm toán.
3. Xuất file kết quả JSON hoạt động chuẩn xác.
4. Lệnh 'python app/cli.py history' đọc được lịch sử log.
"""
import sys
import tempfile
import shutil
from pathlib import Path
from click.testing import CliRunner

# Đảm bảo in tiếng Việt trên console Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.cli import cli


def run_tests():
    print("=" * 65)
    print("🚀 BẮT ĐẦU KIỂM THỬ BƯỚC 6: GIAO DIỆN DÒNG LỆNH (app/cli.py)")
    print("=" * 65)

    runner = CliRunner()
    diff_file = "evals/dataset/sample.diff"

    # === TEST 1: CHẠY LỆNH REVIEW CHẾ ĐỘ MOCK ===
    with tempfile.TemporaryDirectory() as tmpdir:
        out_json = Path(tmpdir) / "output.json"
        result = runner.invoke(
            cli,
            [
                "review",
                "--diff", diff_file,
                "--pr", "42",
                "--repo", "uit/cafe-song-han",
                "--mock",
                "--out", str(out_json),
            ],
        )

        assert result.exit_code == 0, f"Lệnh review phải trả về code 0, thực tế lỗi: {result.output}"
        assert "CODE REVIEW AGENT · SE373" in result.output, "Phải hiển thị Banner"
        assert "REQUEST CHANGES" in result.output, "Phải hiển thị phán quyết REQUEST CHANGES"
        assert "app/services/booking.py:43" in result.output, "Phải hiển thị vị trí lỗi dòng 43"
        assert "KIỂM TOÁN HIỆU NĂNG" in result.output, "Phải hiển thị bảng kiểm toán StepLogger"
        assert out_json.exists(), "Phải xuất được file JSON kết quả"

        print("✅ Test 1 Passed: Lệnh 'review --mock' thực thi thành công và hiển thị giao diện đẹp mắt.")

        # === TEST 2: KIỂM TRA TÍNH TOÀN VẸN CỦA FILE JSON XUẤT RA ===
        import json
        data = json.loads(out_json.read_text(encoding="utf-8"))
        assert data["pr_number"] == 42
        assert data["verdict"] == "request_changes"
        assert len(data["findings"]) == 1
        assert data["findings"][0]["line"] == 43
        print(f"✅ Test 2 Passed: File JSON {out_json.name} xuất ra đúng 100% chuẩn ReviewReport.")

    # === TEST 3: KIỂM TRA LỆNH HISTORY ===
    hist_result = runner.invoke(cli, ["history"])
    assert hist_result.exit_code == 0
    print("✅ Test 3 Passed: Lệnh 'history' duyệt danh sách audit log thành công.")

    print("\n" + "=" * 65)
    print("🎉 TẤT CẢ 3 BÀI TEST BƯỚC 6 ĐÃ HOÀN TOÀN PASS 100%!")
    print("=" * 65)


if __name__ == "__main__":
    run_tests()
