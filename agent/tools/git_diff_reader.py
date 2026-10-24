"""
agent/tools/git_diff_reader.py — Công Cụ Bóc Tách Git Diff (Tools Harness)
========================================================================
"""
from __future__ import annotations

from dataclasses import dataclass, field

from unidiff import PatchSet


@dataclass
class ParsedFile:
    path: str
    added_lines: list[int] = field(default_factory=list)      # Các dòng mới thêm (+)
    removed_lines: list[int] = field(default_factory=list)    # Các dòng bị xóa (-)
    all_valid_lines: set[int] = field(default_factory=set)    # Toàn bộ các dòng hợp lệ trong hunk
    is_new_file: bool = False
    is_deleted_file: bool = False


@dataclass
class ParsedDiff:
    files: list[ParsedFile] = field(default_factory=list)

    @property
    def changed_file_paths(self) -> list[str]:
        return [f.path for f in self.files]

    def get_file(self, file_path: str) -> ParsedFile | None:
        for f in self.files:
            if f.path == file_path:
                return f
        return None

    def validate_finding(self, file_path: str, line: int) -> tuple[bool, str]:

        parsed_file = self.get_file(file_path)
        if not parsed_file:
            return False, f"File '{file_path}' không hề tồn tại trong git diff!"

        if line not in parsed_file.all_valid_lines:
            return False, f"Dòng {line} nằm ngoài các vùng thay đổi (hunks) của file '{file_path}'!"

        return True, ""


class GitDiffReader:
    """
    Công cụ bóc tách Git Diff bằng thư viện unidiff.
    """

    def parse(self, diff_text: str) -> ParsedDiff:
        """
        Nhận vào chuỗi văn bản git diff thô và phân tích thành ParsedDiff.
        """
        if not diff_text or not diff_text.strip():
            return ParsedDiff()

        try:
            patch_set = PatchSet(diff_text)
        except Exception:
            # Xử lý an toàn khi diff bị lỗi định dạng
            return ParsedDiff()

        parsed_files: list[ParsedFile] = []

        for patched_file in patch_set:
            path = patched_file.path

            added: list[int] = []
            removed: list[int] = []
            valid_lines: set[int] = []

            for hunk in patched_file:
                for line in hunk:
                    # target_line_no là số dòng ở phiên bản mới (HEAD)
                    if line.target_line_no is not None:
                        valid_lines.append(line.target_line_no)
                        if line.is_added:
                            added.append(line.target_line_no)

                    # source_line_no là số dòng ở phiên bản cũ (trước khi sửa)
                    if line.source_line_no is not None and line.is_removed:
                        removed.append(line.source_line_no)

            parsed_files.append(
                ParsedFile(
                    path=path,
                    added_lines=sorted(added),
                    removed_lines=sorted(removed),
                    all_valid_lines=set(valid_lines),
                    is_new_file=patched_file.is_added_file,
                    is_deleted_file=patched_file.is_removed_file,
                )
            )

        return ParsedDiff(files=parsed_files)

    def get_summary(self, parsed: ParsedDiff) -> dict:
        """Tóm tắt nhanh số lượng file và dòng thay đổi trong PR."""
        total_added = sum(len(f.added_lines) for f in parsed.files)
        total_removed = sum(len(f.removed_lines) for f in parsed.files)
        return {
            "total_files": len(parsed.files),
            "total_added_lines": total_added,
            "total_removed_lines": total_removed,
            "files": parsed.changed_file_paths,
        }
