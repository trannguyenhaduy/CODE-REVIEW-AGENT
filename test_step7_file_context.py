"""
test_step7_file_context.py — Kiểm thử Tool 2: FileContextReader
==============================================================
Kiểm tra toàn diện các tính năng của Tool 2:
1. Đọc cửa sổ dòng (read_around_line) có đánh số dòng trực quan.
2. Đọc phân đoạn file (read_file).
3. Xử lý an toàn khi file không tồn tại.
4. Chốt chặn bảo mật chống Path Traversal (CẤM đọc ngoài workspace).
5. LangChain @tool wrapper get_file_context.
"""
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from agent.tools.file_context_reader import FileContextReader, get_file_context



def test_file_context_reader():
    print("=" * 65)
    print("🧪 BẮT ĐẦU KIỂM THỬ TOOL 2: FILE CONTEXT READER")
    print("=" * 65)

    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        sample_file = root / "sample_service.py"
        sample_file.write_text(
            "\n".join(f"line_{i:02d} = {i * 10}" for i in range(1, 51)),
            encoding="utf-8",
        )

        reader = FileContextReader(workspace_root=root)

        # 1. Test read_around_line
        ctx = reader.read_around_line("sample_service.py", line=25, window=3)
        assert ctx.exists is True, "File phải tồn tại"
        assert ctx.start_line == 22, f"start_line kỳ vọng 22, nhận {ctx.start_line}"
        assert ctx.end_line == 28, f"end_line kỳ vọng 28, nhận {ctx.end_line}"
        assert ctx.total_lines == 50, f"total_lines kỳ vọng 50, nhận {ctx.total_lines}"
        assert "  25 | line_25 = 250" in ctx.content, "Nội dung phải có đánh số dòng"
        print("✅ Test 1 Passed: read_around_line trích xuất chuẩn cửa sổ dòng (22 -> 28).")

        # 2. Test read_file
        ctx_file = reader.read_file("sample_service.py", start_line=1, max_lines=5)
        assert ctx_file.start_line == 1
        assert ctx_file.end_line == 5
        assert "   1 | line_01 = 10" in ctx_file.content
        print("✅ Test 2 Passed: read_file đọc chuẩn phân đoạn đầu file (1 -> 5).")

        # 3. Test non-existent file
        ctx_missing = reader.read_around_line("ghost_file.py", line=10)
        assert ctx_missing.exists is False
        assert "File không tồn tại" in (ctx_missing.error or "")
        print("✅ Test 3 Passed: File không tồn tại được xử lý an toàn (exists=False).")

        # 4. Test Path Traversal Protection
        ctx_hack = reader.read_around_line("../../secret.env", line=1)
        assert ctx_hack.exists is False
        assert "Truy cập bị từ chối" in (ctx_hack.error or "")
        print("🛡️ Test 4 Passed: Chốt chặn Path Traversal đã chặn đứng truy cập ngoài workspace!")

        # 5. Test LangChain @tool wrapper
        # Trỏ tool vào sample_file trong root
        # Gọi tool với file_path hợp lệ trong repo
        tool_res = get_file_context.invoke({"file_path": "pyproject.toml", "line": 5, "window": 2})
        assert "pyproject.toml" in tool_res
        assert "|" in tool_res
        print("✅ Test 5 Passed: LangChain @tool get_file_context chạy thành công.")

    print("\n" + "=" * 65)
    print("🎉 TẤT CẢ 5 BÀI TEST CỦA TOOL 2 ĐÃ HOÀN TOÀN PASS 100%!")
    print("=" * 65)


if __name__ == "__main__":
    test_file_context_reader()
