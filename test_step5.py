"""
test_step5.py — Kịch bản kiểm thử Bước 5: Bộ Não LangGraph (agent/graph.py)
==========================================================================
Chạy file này để xác nhận:
1. Đồ thị LangGraph StateGraph được biên dịch thành công.
2. Quy trình 4 Nodes (Parse -> Guard -> Review -> Validate) hoạt động mượt mà.
3. Hộp đen StepLogger ghi lại trọn vẹn nhật ký 4 bước kiểm toán.
4. Cổng an ninh Guardrail chặn đứng các trường hợp diff bất thường.
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
from agent import (
    create_review_graph,
    run_code_review,
    ReviewVerdict,
    Severity,
    StepLogger,
)

SAMPLE_DIFF_PATH = Path("evals/dataset/sample.diff")


def run_tests():
    print("=" * 65)
    print("🚀 BẮT ĐẦU KIỂM THỬ BƯỚC 5: BỘ NÃO LANGGRAPH (agent/graph.py)")
    print("=" * 65)

    temp_dir = Path(tempfile.mkdtemp(prefix="test_step5_"))
    diff_text = SAMPLE_DIFF_PATH.read_text(encoding="utf-8")

    try:
        # === TEST 1: KIỂM TRA BIÊN DỊCH GRAPH ===
        graph = create_review_graph()
        assert graph is not None, "Đồ thị LangGraph phải biên dịch thành công"
        print("✅ Test 1 Passed: Biên dịch LangGraph StateGraph thành công.")

        # === TEST 2: KIỂM TRA LUỒNG CHẠY END-TO-END (MOCK LLM) ===
        # Giả lập phản hồi từ LLM: AI phát hiện 1 lỗi đúng dòng 43 và 1 lỗi bịa dòng 999
        mock_llm_response = AIMessage(
            content="""```json
{
  "summary": "Phát hiện lỗi logic nghiêm trọng ở hàm check_capacity làm đảo ngược điều kiện.",
  "findings": [
    {
      "file": "app/services/booking.py",
      "line": 43,
      "side": "RIGHT",
      "severity": "major",
      "category": "bug",
      "message": "Toán tử so sánh bị đảo ngược từ >= thành <= dẫn đến việc bàn quá tải.",
      "suggestion": "    return table.max_capacity >= requested",
      "confidence": 0.98
    },
    {
      "file": "app/services/booking.py",
      "line": 999,
      "side": "RIGHT",
      "severity": "minor",
      "category": "style",
      "message": "Lỗi ảo giác nằm ngoài diff cần bị chặn.",
      "suggestion": null,
      "confidence": 0.5
    }
  ]
}
```"""
        )
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_llm_response
        mock_llm.model_name = "mock-llm-flash"

        logger = StepLogger(run_id="run_step5_demo", log_dir=str(temp_dir))

        report = run_code_review(
            diff_text=diff_text,
            pr_number=42,
            commit_sha="c1eedb",
            repo="uit/cafe-booking",
            custom_llm=mock_llm,
            logger=logger,
        )

        # Kiểm tra tính toàn vẹn của Báo Cáo
        assert report.pr_number == 42
        assert report.commit_sha == "c1eedb"
        assert report.verdict == ReviewVerdict.REQUEST_CHANGES, (
            f"Phán quyết phải là REQUEST_CHANGES (do có lỗi major), thực tế: {report.verdict}"
        )

        # Cổng an ninh phải lọc bỏ dòng 999, chỉ giữ lại dòng 43
        assert len(report.findings) == 1, f"Chỉ được có đúng 1 finding hợp lệ, thực tế: {len(report.findings)}"
        assert report.findings[0].line == 43
        assert report.findings[0].severity == Severity.MAJOR

        print("✅ Test 2 Passed: Luồng End-to-End hoàn chỉnh:")
        print(f"   • Phán quyết PR: {report.verdict.value.upper()}")
        print(f"   • Số finding đăng inline: {len(report.findings)} (dòng {report.findings[0].line})")
        print(f"   • Tóm tắt: {report.summary}")

        # === TEST 3: KIỂM TRA HỘP ĐEN GHI VẾT (STEP LOGGER) ===
        records = logger.read_records()
        step_names = [r["step_name"] for r in records]
        assert "parse_diff" in step_names, "Phải ghi nhận bước parse_diff"
        assert "guard_check" in step_names, "Phải ghi nhận bước guard_check"
        assert "llm_review" in step_names, "Phải ghi nhận bước llm_review"
        assert "validate_and_verdict" in step_names, "Phải ghi nhận bước validate_and_verdict"
        print(f"✅ Test 3 Passed: Hộp đen StepLogger ghi nhận đủ 4 bước kiểm toán: {step_names}")

        # === TEST 4: KIỂM TRA GUARDRAIL BẢO VỆ CHỐNG DIFF RỖNG ===
        guard_logger = StepLogger(run_id="run_guard_test", log_dir=str(temp_dir))
        empty_report = run_code_review(
            diff_text="",
            pr_number=99,
            logger=guard_logger,
        )
        assert empty_report.verdict == ReviewVerdict.COMMENT
        assert "Git Diff rỗng" in empty_report.summary
        assert len(empty_report.findings) == 0
        print("✅ Test 4 Passed: Guardrail kích hoạt an toàn khi diff rỗng (không đốt token).")

        print("\n" + "=" * 65)
        print("🎉 TẤT CẢ CÁC BÀI TEST BƯỚC 5 ĐÃ HOÀN TOÀN PASS 100%!")
        print("=" * 65)

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    run_tests()
