"""
agent/tools/file_context_reader.py — Công Cụ Đọc Ngữ Cảnh Mã Nguồn (Tool 2)
===========================================================================
Cung cấp khả năng mở rộng tầm nhìn cho Agent:
- Đọc các dòng mã nguồn xung quanh vùng diff hunk (Class, Function enclosing, imports).
- Bảo vệ an toàn chống Path Traversal (chỉ đọc file trong workspace).
- Đánh số dòng trực quan giúp LLM đối soát chính xác toạ độ dòng.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from langchain_core.tools import tool


@dataclass
class FileContext:
    file_path: str
    start_line: int
    end_line: int
    total_lines: int
    content: str
    exists: bool = True
    error: str | None = None


class FileContextReader:


    def __init__(self, workspace_root: str | Path = "."):
        self.workspace_root = Path(workspace_root).resolve()

    def _resolve_safe_path(self, relative_path: str) -> tuple[Path | None, str | None]:
        """Kiểm tra và chuẩn hóa đường dẫn để tránh lỗ hổng Path Traversal."""
        try:
            target_path = (self.workspace_root / relative_path).resolve()
            # Đảm bảo target_path phải nằm bên trong workspace_root
            if not str(target_path).startswith(str(self.workspace_root)):
                return None, f"Truy cập bị từ chối: Đường dẫn '{relative_path}' nằm ngoài thư mục dự án!"
            return target_path, None
        except Exception as e:
            return None, f"Đường dẫn không hợp lệ: {e}"

    def read_around_line(
        self,
        file_path: str,
        line: int,
        window: int = 15,
    ) -> FileContext:

        target_path, err = self._resolve_safe_path(file_path)
        if err or not target_path:
            return FileContext(
                file_path=file_path,
                start_line=0,
                end_line=0,
                total_lines=0,
                content="",
                exists=False,
                error=err,
            )

        if not target_path.exists() or not target_path.is_file():
            return FileContext(
                file_path=file_path,
                start_line=0,
                end_line=0,
                total_lines=0,
                content="",
                exists=False,
                error=f"File không tồn tại trên đĩa: {file_path}",
            )

        try:
            with open(target_path, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except Exception as e:
            return FileContext(
                file_path=file_path,
                start_line=0,
                end_line=0,
                total_lines=0,
                content="",
                exists=False,
                error=f"Không thể đọc file: {e}",
            )

        total_lines = len(lines)
        if total_lines == 0:
            return FileContext(
                file_path=file_path,
                start_line=1,
                end_line=1,
                total_lines=0,
                content="(File rỗng)",
                exists=True,
            )

        # Tính toán toạ độ cửa sổ (1-indexed)
        start_line = max(1, line - window)
        end_line = min(total_lines, line + window)

        # Trích xuất nội dung có đánh số dòng
        window_lines = lines[start_line - 1 : end_line]
        formatted_content = "".join(
            f"{i + start_line:4d} | {l}" for i, l in enumerate(window_lines)
        )

        return FileContext(
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            total_lines=total_lines,
            content=formatted_content,
            exists=True,
        )

    def read_file(
        self,
        file_path: str,
        start_line: int = 1,
        max_lines: int = 100,
    ) -> FileContext:
        """Đọc một đoạn file từ start_line đến tối đa max_lines dòng."""
        target_path, err = self._resolve_safe_path(file_path)
        if err or not target_path:
            return FileContext(
                file_path=file_path,
                start_line=0,
                end_line=0,
                total_lines=0,
                content="",
                exists=False,
                error=err,
            )

        if not target_path.exists() or not target_path.is_file():
            return FileContext(
                file_path=file_path,
                start_line=0,
                end_line=0,
                total_lines=0,
                content="",
                exists=False,
                error=f"File không tồn tại trên đĩa: {file_path}",
            )

        try:
            with open(target_path, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except Exception as e:
            return FileContext(
                file_path=file_path,
                start_line=0,
                end_line=0,
                total_lines=0,
                content="",
                exists=False,
                error=f"Không thể đọc file: {e}",
            )

        total_lines = len(lines)
        start_line = max(1, start_line)
        end_line = min(total_lines, start_line + max_lines - 1)

        window_lines = lines[start_line - 1 : end_line]
        formatted_content = "".join(
            f"{i + start_line:4d} | {l}" for i, l in enumerate(window_lines)
        )

        return FileContext(
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            total_lines=total_lines,
            content=formatted_content,
            exists=True,
        )


@tool(description="Đọc các dòng mã nguồn ngữ cảnh xung quanh dòng line của một file trong repo.")
def get_file_context(file_path: str, line: int, window: int = 15) -> str:
    """Đọc ngữ cảnh mã nguồn xung quanh dòng code bị sửa."""

    reader = FileContextReader()
    ctx = reader.read_around_line(file_path, line, window)
    if not ctx.exists:
        return f"Lỗi đọc file: {ctx.error}"
    return f"--- Ngữ cảnh {file_path} (Dòng {ctx.start_line} đến {ctx.end_line}/{ctx.total_lines}) ---\n{ctx.content}"
