"""
agent/tools/file_context_reader.py — Tool 2: FileContextReader
===============================================================
Đọc nội dung file trong repo tại một git ref cụ thể.

THIẾT KẾ QUAN TRỌNG:
- Read-only: chỉ đọc, KHÔNG ghi vào file
- Denylist: chặn đọc file bí mật (.env, *.pem, id_rsa, ...)
- Giới hạn kích thước: tránh token explosion
- Path traversal protection: chặn ../../../ attacks
- Allowlist repo: chỉ đọc repo được phép
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

# ─────────────────────────────────────────────────────────────
# Security Constants
# ─────────────────────────────────────────────────────────────

# File patterns bị cấm đọc tuyệt đối
SECRET_FILE_DENYLIST = [
    r"\.env$",
    r"\.env\.",
    r"\.pem$",
    r"\.key$",
    r"id_rsa$",
    r"id_rsa\.pub$",
    r"id_ed25519$",
    r"\.p12$",
    r"\.pfx$",
    r"\.git/config$",
    r"\.git/",
    r"secrets\.",
    r"credentials\.",
    r"private_key",
    r"service_account\.json$",
]

MAX_FILE_SIZE_BYTES = 100_000  # 100KB - giới hạn tránh đốt token
MAX_LINES_TO_RETURN = 200      # Tối đa 200 dòng mỗi lần đọc


class FileContextReader:
    """
    Tool 2: Đọc nội dung file trong repo để bổ sung context cho agent.
    
    Sử dụng:
        reader = FileContextReader(repo_root="/path/to/repo")
        content = reader.read_file("app/services/booking.py", start_line=35, end_line=55)
        
        # Tìm kiếm trong code
        results = reader.search_code("def calc_fee", file_pattern="*.py")
    """
    
    def __init__(
        self, 
        repo_root: str | Path,
        max_file_size: int = MAX_FILE_SIZE_BYTES,
        max_lines: int = MAX_LINES_TO_RETURN,
        extra_denylist: Optional[list[str]] = None,
    ):
        self.repo_root = Path(repo_root).resolve()
        self.max_file_size = max_file_size
        self.max_lines = max_lines
        self._denylist = [
            re.compile(p, re.IGNORECASE) 
            for p in SECRET_FILE_DENYLIST + (extra_denylist or [])
        ]
    
    def _is_secret_file(self, path: str) -> bool:
        """Kiểm tra file có nằm trong denylist secrets không."""
        return any(p.search(path) for p in self._denylist)
    
    def _resolve_safe_path(self, relative_path: str) -> Path:
        """
        Resolve đường dẫn file an toàn — chặn path traversal.
        
        Raises:
            PermissionError: nếu path traversal hoặc đọc file bí mật
        """
        # Chặn null bytes
        if "\x00" in relative_path:
            raise PermissionError("Path chứa null byte — bị chặn")
        
        # Normalize và resolve
        try:
            full_path = (self.repo_root / relative_path).resolve()
        except Exception as e:
            raise PermissionError(f"Path không hợp lệ: {e}") from e
        
        # Đảm bảo path nằm trong repo root (chặn ../../../)
        try:
            full_path.relative_to(self.repo_root)
        except ValueError:
            raise PermissionError(
                f"Path traversal bị chặn: '{relative_path}' nằm ngoài repo"
            )
        
        # Kiểm tra denylist
        if self._is_secret_file(relative_path) or self._is_secret_file(str(full_path)):
            raise PermissionError(
                f"File bí mật bị chặn: '{relative_path}'"
            )
        
        return full_path
    
    def read_file(
        self, 
        relative_path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
    ) -> dict:
        """
        Đọc nội dung file (hoặc một phần) trong repo.
        
        Args:
            relative_path: Đường dẫn file tương đối từ gốc repo
            start_line: Dòng bắt đầu (1-indexed, inclusive)
            end_line: Dòng kết thúc (1-indexed, inclusive)
            
        Returns:
            {
                "path": str,
                "content": str,
                "start_line": int,
                "end_line": int,
                "total_lines": int,
                "truncated": bool,
            }
        """
        full_path = self._resolve_safe_path(relative_path)
        
        if not full_path.exists():
            return {
                "error": f"File không tồn tại: '{relative_path}'",
                "path": relative_path,
            }
        
        if not full_path.is_file():
            return {
                "error": f"Không phải file: '{relative_path}'",
                "path": relative_path,
            }
        
        # Kiểm tra kích thước
        file_size = full_path.stat().st_size
        if file_size > self.max_file_size:
            return {
                "error": (
                    f"File quá lớn ({file_size:,} bytes > {self.max_file_size:,} bytes). "
                    f"Dùng start_line/end_line để chỉ đọc phần cần thiết."
                ),
                "path": relative_path,
                "file_size_bytes": file_size,
            }
        
        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return {"error": f"Không đọc được file: {e}", "path": relative_path}
        
        all_lines = content.splitlines(keepends=True)
        total_lines = len(all_lines)
        
        # Xác định range
        s = max(1, start_line or 1) - 1  # 0-indexed
        e = min(total_lines, end_line or total_lines)
        
        # Giới hạn số dòng trả về
        if e - s > self.max_lines:
            e = s + self.max_lines
            truncated = True
        else:
            truncated = False
        
        selected_lines = all_lines[s:e]
        
        # Thêm số dòng vào đầu mỗi dòng để agent dễ tham chiếu
        numbered_lines = [
            f"{s + i + 1:4d} | {line}" 
            for i, line in enumerate(selected_lines)
        ]
        
        return {
            "path": relative_path,
            "content": "".join(numbered_lines),
            "start_line": s + 1,
            "end_line": s + len(selected_lines),
            "total_lines": total_lines,
            "truncated": truncated,
        }
    
    def read_lines_around(
        self, 
        relative_path: str, 
        center_line: int, 
        context_lines: int = 10
    ) -> dict:
        """
        Đọc nội dung xung quanh một dòng cụ thể.
        Tiện ích cho agent khi muốn xem context của một finding.
        """
        start = max(1, center_line - context_lines)
        end = center_line + context_lines
        return self.read_file(relative_path, start_line=start, end_line=end)
    
    def search_code(
        self, 
        query: str, 
        file_pattern: str = "*.py",
        max_results: int = 10,
    ) -> dict:
        """
        Tìm kiếm text trong các file của repo.
        
        Args:
            query: Text cần tìm (không phải regex)
            file_pattern: Glob pattern lọc file (ví dụ: "*.py", "*.ts")
            max_results: Số kết quả tối đa
            
        Returns:
            {"matches": [{"file", "line_no", "content"}], "total_found": int}
        """
        matches = []
        query_lower = query.lower()
        
        for file_path in self.repo_root.rglob(file_pattern):
            # Bỏ qua file bí mật
            rel_path = str(file_path.relative_to(self.repo_root))
            if self._is_secret_file(rel_path):
                continue
            
            # Bỏ qua thư mục ẩn và venv
            if any(part.startswith(".") or part in ("venv", "__pycache__", "node_modules") 
                   for part in file_path.parts):
                continue
            
            if file_path.stat().st_size > self.max_file_size:
                continue
            
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            
            for line_no, line in enumerate(content.splitlines(), 1):
                if query_lower in line.lower():
                    matches.append({
                        "file": rel_path,
                        "line_no": line_no,
                        "content": line.strip(),
                    })
                    if len(matches) >= max_results:
                        return {
                            "matches": matches,
                            "total_found": f"≥ {max_results} (truncated)",
                            "query": query,
                        }
        
        return {
            "matches": matches,
            "total_found": len(matches),
            "query": query,
        }
    
    def list_files(self, directory: str = "", file_pattern: str = "*") -> dict:
        """Liệt kê file trong một thư mục (để agent khám phá repo)."""
        safe_dir = self._resolve_safe_path(directory) if directory else self.repo_root
        
        files = []
        for p in safe_dir.rglob(file_pattern):
            if p.is_file():
                rel = str(p.relative_to(self.repo_root))
                if not self._is_secret_file(rel):
                    files.append(rel)
        
        return {"files": sorted(files)[:100], "directory": directory or "."}


# ─────────────────────────────────────────────────────────────
# LangChain Tool Wrappers
# ─────────────────────────────────────────────────────────────

def create_file_context_tools(repo_root: str):
    """Tạo các LangChain tool wrapper cho FileContextReader."""
    try:
        from langchain_core.tools import tool
    except ImportError:
        return []
    
    reader = FileContextReader(repo_root=repo_root)
    
    @tool
    def read_file_at_ref(relative_path: str, start_line: int = 1, end_line: int = 50) -> dict:
        """
        Đọc nội dung file trong repo để lấy thêm context.
        Dùng khi cần hiểu ngữ cảnh xung quanh một dòng trong diff.
        
        Args:
            relative_path: Đường dẫn file tương đối từ gốc repo
            start_line: Dòng bắt đầu đọc (1-indexed)
            end_line: Dòng kết thúc đọc (1-indexed)
        """
        return reader.read_file(relative_path, start_line=start_line, end_line=end_line)
    
    @tool
    def search_code(query: str, file_pattern: str = "*.py") -> dict:
        """
        Tìm kiếm text trong code base.
        Dùng khi cần tìm nơi một hàm được gọi, hay biến được sử dụng.
        
        Args:
            query: Text cần tìm trong code
            file_pattern: Glob pattern để lọc loại file (*.py, *.ts, ...)
        """
        return reader.search_code(query, file_pattern=file_pattern)
    
    return [read_file_at_ref, search_code]
