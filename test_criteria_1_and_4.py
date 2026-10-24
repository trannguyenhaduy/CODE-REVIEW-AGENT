"""
test_criteria_1_and_4.py — Kiểm tra Tiêu chí 1 (Self-Correction) & Tiêu chí 4 (Syntax Check)
============================================================================================
Chạy script này để xác nhận:
1. Tiêu chí 4: FindingValidator dùng ast.parse kiểm tra cú pháp suggestion, chặn đứng code lỗi cú pháp.
2. Tiêu chí 1: Agent phát hiện output sai schema và tự động gửi prompt yêu cầu LLM sửa lại tối đa 2 lần.
3. Khi quá 2 lần sửa, Agent tự động bỏ finding lỗi và ghi nhận vào audit trace log.
"""
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock

# Đảm bảo in tiếng Việt trên console Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from langchain_core.messages import AIMessage
from agent.schemas import ReviewFinding, Severity, Category
from agent.harness.validator import FindingValidator
from agent.harness.step_logger import StepLogger
from agent.graph import run_code_review

SAMPLE_DIFF = Path("evals/dataset/sample.diff").read_text(encoding="utf-8")


def run_tests():
    print("=" * 70)
    print("🚀 BẮT ĐẦU KIỂM THỬ: TIÊU CHÍ 1 (SELF-CORRECTION) & TIÊU CHÍ 4 (SYNTAX CHECK)")
    print("=" * 70)

    # =========================================================================
    # PHẦN 1: KIỂM THỬ TIÊU CHÍ 4 (SYNTAX CHECK BẰNG AST.PARSE)
    # =========================================================================
    print("\n--- [TIÊU CHÍ 4] Kiểm định cú pháp của Suggestion ---")
    validator = FindingValidator()

    # Ca 1.1: Suggestion chuẩn cú pháp Python
    valid_f = ReviewFinding(
        file="app/services/booking.py",
        line=43,
        severity=Severity.MAJOR,
        category=Category.LOGIC,
        message="Toán tử bị đảo ngược cần sửa lại.",
        suggestion="    return table.max_capacity >= requested",
    )
    res1 = validator.validate_single(valid_f)
    assert res1.is_valid, f"Suggestion hợp lệ phải PASS, lỗi: {res1.errors}"
    print("✅ Test 1.1 Passed: Suggestion Python hợp lệ ('return >= requested') được chấp thuận.")

    # Ca 1.2: Suggestion sai cú pháp Python (SyntaxError)
    broken_f = ReviewFinding(
        file="app/services/booking.py",
        line=43,
        severity=Severity.MAJOR,
        category=Category.LOGIC,
        message="Gợi ý sửa code bị lỗi cú pháp.",
        suggestion="    return >= >= def broken():",  # Cú pháp sai lè!
    )
    res2 = validator.validate_single(broken_f)
    assert not res2.is_valid, "Suggestion sai cú pháp phải bị Validator phát hiện!"
    assert any("Syntax Error" in e for e in res2.errors)
    print(f"🛡️ Test 1.2 Passed: Validator đã chặn đứng code sai cú pháp: {res2.errors}")

    # =========================================================================
    # PHẦN 2: KIỂM THỬ TIÊU CHÍ 1 (SELF-CORRECTION LOOP TỐI ĐA 2 LẦN)
    # =========================================================================
    print("\n--- [TIÊU CHÍ 1] Vòng lặp Agent Tự Sửa Schema (Self-Correction) ---")
    temp_dir = Path(tempfile.mkdtemp(prefix="test_self_correct_"))

    try:
        # Ca 2.1: Lần 1 trả về JSON sai schema, Lần 2 AI tự sửa lại thành công
        bad_response = AIMessage(
            content='{"findings": [{"file": "app/services/booking.py", "line": -99, "severity": "major", "category": "logic", "message": "Số dòng bị âm!", "confidence": 0.9}]}'
        )
        good_response = AIMessage(
            content='{"summary": "Đã tự sửa schema!", "findings": [{"file": "app/services/booking.py", "line": 43, "severity": "major", "category": "logic", "message": "Đã sửa số dòng thành 43 hợp lệ", "confidence": 0.95}]}'
        )

        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = [bad_response, good_response]
        mock_llm.model_name = "mock-llm"

        logger = StepLogger(run_id="run_self_correct_demo", log_dir=str(temp_dir))

        report = run_code_review(
            diff_text=SAMPLE_DIFF,
            pr_number=42,
            custom_llm=mock_llm,
            logger=logger,
        )

        # Xác nhận AI đã gọi lại LLM lần 2 để tự sửa
        assert mock_llm.invoke.call_count == 2, f"Phải gọi LLM 2 lần, thực tế: {mock_llm.invoke.call_count}"
        assert len(report.findings) == 1
        assert report.findings[0].line == 43

        # Kiểm tra Hộp đen ghi log trace
        records = logger.read_records()
        step_names = [r["step_name"] for r in records]
        assert "self_correction_attempt" in step_names, "Phải ghi nhận bước self_correction_attempt vào trace"
        print(f"✅ Test 2.1 Passed: Agent phát hiện lỗi schema, kích hoạt Self-Correction và tự sửa thành công!")
        print(f"   • Số lần gọi LLM: {mock_llm.invoke.call_count}")
        print(f"   • Nhật ký ghi vết trace: {step_names}")

        # Ca 2.2: AI sửa quá 2 lần vẫn sai -> Bỏ finding lỗi và ghi vào trace log
        hopeless_llm = MagicMock()
        hopeless_llm.invoke.return_value = bad_response  # Liên tục trả về dữ liệu sai line = -99
        hopeless_llm.model_name = "mock-hopeless"

        logger2 = StepLogger(run_id="run_exhausted_demo", log_dir=str(temp_dir))
        report2 = run_code_review(
            diff_text=SAMPLE_DIFF,
            pr_number=42,
            custom_llm=hopeless_llm,
            logger=logger2,
        )

        # 1 lần gọi ban đầu + 2 lần retry = 3 lần invoke
        assert hopeless_llm.invoke.call_count == 3, f"Phải dừng lại sau 3 lần (1 gốc + 2 retry), thực tế: {hopeless_llm.invoke.call_count}"
        assert len(report2.findings) == 0, "Quá số lần thì phải bỏ finding lỗi đó đi"

        records2 = logger2.read_records()
        step_names2 = [r["step_name"] for r in records2]
        assert "self_correction_exhausted" in step_names2, "Phải ghi nhận self_correction_exhausted vào trace"
        print(f"🛡️ Test 2.2 Passed: Quá 2 lần tự sửa, Agent tự động bỏ finding lỗi và ghi nhận vào trace log!")
        print(f"   • Nhật ký ghi vết trace: {step_names2}")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    print("\n" + "=" * 70)
    print("🎉 HOÀN THÀNH 100%! CẢ TIÊU CHÍ 1 VÀ TIÊU CHÍ 4 ĐÃ ĐẠT CHUẨN XUẤT SẮC!")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
