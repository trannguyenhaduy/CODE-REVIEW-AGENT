"""
test_step4.py — Kiểm tra hộp đen ghi vết (StepLogger)
=====================================================
Chạy script này để xác nhận:
1. Ghi vết từng bước với latency_ms và token_usage.
2. Context manager tự động bấm giờ và bắt lỗi khi có sự cố.
3. Tệp JSONL được lưu xuống đĩa đúng định dạng, đọc lại nguyên vẹn.
4. Thống kê tổng quan (get_summary) hoạt động chuẩn xác.
"""
import sys
import tempfile
import shutil
from pathlib import Path

# Đảm bảo in tiếng Việt trên console Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from agent.harness import StepLogger


def run_tests():
    print("=" * 65)
    print("🚀 BẮT ĐẦU KIỂM THỬ BƯỚC 4: HỘP ĐEN GHI VẾT (StepLogger)")
    print("=" * 65)

    temp_dir = Path(tempfile.mkdtemp(prefix="test_logger_"))

    try:
        # Test 1: Khởi tạo logger và ghi log trực tiếp
        logger = StepLogger(run_id="run_test_001", log_dir=str(temp_dir))
        assert logger.run_id == "run_test_001", "run_id phải khớp!"
        assert logger.log_file.name == "run_test_001.jsonl", "Tên file phải là run_test_001.jsonl!"

        rec1 = logger.log_step(
            step_name="parse_diff",
            latency_ms=12.5,
            input_data={"raw_len": 500},
            output_data={"files_count": 2},
            token_usage={"prompt": 0, "completion": 0, "total": 0},
        )
        assert rec1.step_index == 0, "Bước đầu tiên phải có index = 0"
        assert rec1.status == "SUCCESS"
        print("✅ Test 1 Passed: Ghi log trực tiếp thành công (step_index=0).")

        # Test 2: Dùng measure_step context manager đo thời gian tự động
        with logger.measure_step("llm_review", input_data={"prompt_tokens": 150}) as ctx:
            # Giả lập thời gian chạy 50ms
            import time
            time.sleep(0.05)
            ctx.output_data = {"findings_count": 3}
            ctx.token_usage = {"prompt": 150, "completion": 85, "total": 235}

        assert len(logger.records) == 2, "Phải có đúng 2 bản ghi trong memory"
        rec2 = logger.records[1]
        assert rec2.step_name == "llm_review"
        assert rec2.latency_ms >= 40.0, f"Latency phải >= 40ms, thực tế: {rec2.latency_ms}ms"
        assert rec2.token_usage["total"] == 235
        print(f"✅ Test 2 Passed: measure_step tự động bấm giờ ({rec2.latency_ms}ms) và lưu tokens.")

        # Test 3: Xử lý khi có lỗi xảy ra trong bước chạy
        try:
            with logger.measure_step("failed_step", input_data={"data": 123}):
                raise ValueError("Cố tình ném lỗi giả lập!")
        except ValueError:
            pass  # Lỗi được ném ra ngoài như bình thường

        assert len(logger.records) == 3
        rec3 = logger.records[2]
        assert rec3.status == "FAILED", "Trạng thái phải là FAILED khi có lỗi"
        assert "Cố tình ném lỗi giả lập!" in (rec3.error or "")
        print("✅ Test 3 Passed: measure_step bắt lỗi chuẩn xác và ghi nhận status='FAILED'.")

        # Test 4: Đọc lại file JSONL từ đĩa để xác nhận độ bền bỉ
        disk_records = logger.read_records()
        assert len(disk_records) == 3, f"Phải đọc được 3 dòng từ file JSONL, thực tế: {len(disk_records)}"
        assert disk_records[0]["step_name"] == "parse_diff"
        assert disk_records[1]["step_name"] == "llm_review"
        assert disk_records[2]["step_name"] == "failed_step"
        print(f"✅ Test 4 Passed: Đọc file {logger.log_file.name} trên đĩa thành công (3 dòng JSONL).")

        # Test 5: Thống kê tổng quan phiên chạy
        summary = logger.get_summary()
        assert summary["run_id"] == "run_test_001"
        assert summary["total_steps"] == 3
        assert summary["token_usage"]["total"] == 235
        assert summary["status"] == "FAILED"  # Vì có step 3 bị failed
        assert summary["failed_steps"] == ["failed_step"]
        print("✅ Test 5 Passed: Báo cáo tổng quan get_summary() tính toán chính xác.")

        print("\n" + "=" * 65)
        print("🎉 TẤT CẢ 5 TESTS CỦA BƯỚC 4 ĐÃ PASS 100%!")
        print("=" * 65)

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    run_tests()
