"""
agent/tools/git_diff_reader.py — Tool 1: GitDiffReader
=======================================================
Parse git diff patch thành structured data (file, hunk, dòng hợp lệ).

THIẾT KẾ QUAN TRỌNG (theo yêu cầu đề tài UC-01):
- Dùng thư viện `unidiff` để parse — KHÔNG để LLM tự đếm dòng
- Sinh ra bảng ánh xạ: line_number → valid (True/False)
- Agent dùng bảng này để validate finding TRƯỚC khi sinh output
- Bất kỳ finding nào trỏ ra ngoài diff bị Validator Harness loại bỏ
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import unidiff
    from unidiff import PatchSet
except ImportError:
    raise ImportError(
        "Thiếu thư viện `unidiff`. Cài bằng: pip install unidiff"
    )


# ─────────────────────────────────────────────────────────────
# Data Structures
# ─────────────────────────────────────────────────────────────

@dataclass
class DiffLine:
    """Một dòng trong diff với metadata đầy đủ."""
    line_no: int           # Số dòng trong phiên bản HEAD (target)
    source_line_no: int    # Số dòng trong phiên bản gốc (source)
    line_type: str         # "added", "removed", "context"
    value: str             # Nội dung dòng (không kèm +/-/space prefix)
    file: str              # Đường dẫn file


@dataclass  
class DiffFile:
    """Thông tin một file trong diff."""
    path: str              # Đường dẫn file hiện tại (HEAD)
    source_path: str       # Đường dẫn file gốc
    is_new_file: bool
    is_deleted_file: bool
    is_renamed: bool
    added_lines: list[int] = field(default_factory=list)    # Line numbers thêm mới (RIGHT side)
    removed_lines: list[int] = field(default_factory=list)  # Line numbers bị xóa (LEFT side)
    context_lines: list[int] = field(default_factory=list)  # Dòng context (không thay đổi)
    hunks: list["DiffHunk"] = field(default_factory=list)
    
    @property
    def all_valid_lines(self) -> set[int]:
        """Tập hợp TẤT CẢ line numbers hợp lệ để comment (added + context)."""
        return set(self.added_lines) | set(self.context_lines)
    
    def is_line_valid(self, line_no: int) -> bool:
        """Kiểm tra một line_no có hợp lệ để comment không."""
        return line_no in self.all_valid_lines


@dataclass
class DiffHunk:
    """Một hunk trong diff."""
    source_start: int
    source_length: int
    target_start: int
    target_length: int
    lines: list[DiffLine] = field(default_factory=list)


@dataclass
class ParsedDiff:
    """Kết quả parse đầy đủ của một git diff."""
    files: list[DiffFile]
    raw_diff: str
    
    @property
    def changed_file_paths(self) -> list[str]:
        """Danh sách đường dẫn file đã thay đổi."""
        return [f.path for f in self.files]
    
    def get_file(self, path: str) -> Optional[DiffFile]:
        """Lấy DiffFile theo đường dẫn."""
        for f in self.files:
            if f.path == path or f.path.endswith(path):
                return f
        return None
    
    def validate_finding(self, file_path: str, line_no: int) -> tuple[bool, str]:
        """
        Validator harness: kiểm tra finding có hợp lệ không.
        
        Returns:
            (True, "") nếu hợp lệ
            (False, reason) nếu không hợp lệ
        """
        diff_file = self.get_file(file_path)
        if diff_file is None:
            return False, f"File '{file_path}' không có trong diff"
        
        if diff_file.is_deleted_file:
            if line_no in diff_file.removed_lines:
                return True, ""
            return False, f"File đã bị xóa, dòng {line_no} không hợp lệ"
        
        if not diff_file.is_line_valid(line_no):
            valid_range = sorted(diff_file.all_valid_lines)
            sample = valid_range[:5] if valid_range else []
            return False, (
                f"Dòng {line_no} không nằm trong diff của file '{file_path}'. "
                f"Các dòng hợp lệ (mẫu): {sample}"
            )
        
        return True, ""


# ─────────────────────────────────────────────────────────────
# Main Parser
# ─────────────────────────────────────────────────────────────

class GitDiffReader:
    """
    Tool 1: Parse git diff thành structured data.
    
    Sử dụng:
        reader = GitDiffReader()
        parsed = reader.parse(diff_text)
        
        # Kiểm tra finding hợp lệ
        valid, reason = parsed.validate_finding("app/booking.py", 42)
        
        # Lấy danh sách file thay đổi
        files = parsed.changed_file_paths
    """
    
    # File patterns bị bỏ qua hoàn toàn (lock files, generated, migration)
    SKIP_PATTERNS = [
        r"package-lock\.json$",
        r"yarn\.lock$",
        r"poetry\.lock$",
        r"Pipfile\.lock$",
        r"\.min\.(js|css)$",
        r"__snapshots__/.*\.snap$",
        r"migrations/\d{4}_.*\.py$",
        r"\.pb\.go$",            # protobuf generated
        r"_pb2\.py$",            # protobuf python generated
    ]
    
    def __init__(self, skip_patterns: Optional[list[str]] = None):
        self._skip_patterns = [
            re.compile(p) for p in (skip_patterns or self.SKIP_PATTERNS)
        ]
    
    def _should_skip(self, path: str) -> bool:
        """Kiểm tra file có nên bị bỏ qua không."""
        return any(p.search(path) for p in self._skip_patterns)
    
    def parse(self, diff_text: str) -> ParsedDiff:
        """
        Parse raw git diff text thành ParsedDiff.
        
        Args:
            diff_text: Output của `git diff` hoặc GitHub/Bitbucket PR diff
            
        Returns:
            ParsedDiff với đầy đủ thông tin file, hunk, line mapping
        """
        if not diff_text or not diff_text.strip():
            return ParsedDiff(files=[], raw_diff=diff_text or "")
        
        try:
            patch_set = PatchSet(diff_text)
        except Exception as e:
            raise ValueError(f"Không thể parse diff: {e}") from e
        
        diff_files: list[DiffFile] = []
        
        for patched_file in patch_set:
            path = patched_file.path
            
            # Bỏ qua file generated/lock
            if self._should_skip(path):
                continue
            
            source_path = patched_file.source_file or path
            # Loại bỏ prefix a/ b/ trong git diff
            source_path = re.sub(r"^[ab]/", "", source_path)
            path = re.sub(r"^[ab]/", "", path)
            
            diff_file = DiffFile(
                path=path,
                source_path=source_path,
                is_new_file=patched_file.is_added_file,
                is_deleted_file=patched_file.is_removed_file,
                is_renamed=patched_file.is_rename,
            )
            
            # Parse từng hunk
            for hunk in patched_file:
                diff_hunk = DiffHunk(
                    source_start=hunk.source_start,
                    source_length=hunk.source_length,
                    target_start=hunk.target_start,
                    target_length=hunk.target_length,
                )
                
                for line in hunk:
                    if line.is_added:
                        diff_file.added_lines.append(line.target_line_no)
                        diff_hunk.lines.append(DiffLine(
                            line_no=line.target_line_no,
                            source_line_no=0,
                            line_type="added",
                            value=line.value.rstrip("\n"),
                            file=path,
                        ))
                    elif line.is_removed:
                        diff_file.removed_lines.append(line.source_line_no)
                        diff_hunk.lines.append(DiffLine(
                            line_no=0,
                            source_line_no=line.source_line_no,
                            line_type="removed",
                            value=line.value.rstrip("\n"),
                            file=path,
                        ))
                    else:  # context line
                        if line.target_line_no:
                            diff_file.context_lines.append(line.target_line_no)
                        diff_hunk.lines.append(DiffLine(
                            line_no=line.target_line_no or 0,
                            source_line_no=line.source_line_no or 0,
                            line_type="context",
                            value=line.value.rstrip("\n"),
                            file=path,
                        ))
                
                diff_file.hunks.append(diff_hunk)
            
            diff_files.append(diff_file)
        
        return ParsedDiff(files=diff_files, raw_diff=diff_text)
    
    def parse_from_file(self, diff_file_path: str | Path) -> ParsedDiff:
        """Parse từ file diff local."""
        path = Path(diff_file_path)
        if not path.exists():
            raise FileNotFoundError(f"File diff không tồn tại: {diff_file_path}")
        
        return self.parse(path.read_text(encoding="utf-8"))
    
    def get_summary(self, parsed: ParsedDiff) -> dict:
        """Trả về tóm tắt diff để log."""
        return {
            "total_files": len(parsed.files),
            "new_files": sum(1 for f in parsed.files if f.is_new_file),
            "deleted_files": sum(1 for f in parsed.files if f.is_deleted_file),
            "renamed_files": sum(1 for f in parsed.files if f.is_renamed),
            "total_added_lines": sum(len(f.added_lines) for f in parsed.files),
            "total_removed_lines": sum(len(f.removed_lines) for f in parsed.files),
            "files": [f.path for f in parsed.files],
        }


# ─────────────────────────────────────────────────────────────
# LangChain Tool Wrapper
# ─────────────────────────────────────────────────────────────

def create_git_diff_reader_tool():
    """
    Tạo LangChain tool wrapper để dùng trong agent graph.
    Import lazy để tránh lỗi nếu langchain chưa được cài.
    """
    try:
        from langchain_core.tools import tool
    except ImportError:
        return None
    
    reader = GitDiffReader()
    
    @tool
    def get_pr_diff_parsed(diff_text: str) -> dict:
        """
        Parse git diff của PR thành structured data.
        Trả về danh sách file đã thay đổi và bảng ánh xạ dòng hợp lệ.
        Dùng tool này trước khi sinh bất kỳ finding nào để xác định dòng hợp lệ.
        
        Args:
            diff_text: Raw git diff text
            
        Returns:
            Dict với 'files', 'changed_file_paths', 'summary'
        """
        parsed = reader.parse(diff_text)
        return {
            "changed_file_paths": parsed.changed_file_paths,
            "summary": reader.get_summary(parsed),
            "files": {
                f.path: {
                    "added_lines": f.added_lines,
                    "removed_lines": f.removed_lines,
                    "is_new_file": f.is_new_file,
                    "is_deleted_file": f.is_deleted_file,
                }
                for f in parsed.files
            }
        }
    
    return get_pr_diff_parsed
