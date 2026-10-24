"""
agent/harness/validator.py — Lớp Kiểm Định An Toàn (Verification Harness)
========================================================================

"""
from __future__ import annotations

from dataclasses import dataclass, field

from agent.schemas import ReviewFinding, ReviewVerdict, Severity
from agent.tools.git_diff_reader import ParsedDiff


@dataclass
class ValidationResult:
    finding: ReviewFinding
    is_valid: bool
    errors: list[str] = field(default_factory=list)


@dataclass
class BatchValidationResult:
    valid: list[ReviewFinding] = field(default_factory=list)               # Các finding hợp lệ được đăng inline
    invalid: list[tuple[ReviewFinding, list[str]]] = field(default_factory=list)  # Các finding vi phạm bị loại bỏ
    pr_level_comments: list[ReviewFinding] = field(default_factory=list)   # Finding đúng nhưng dòng ngoài diff -> comment cấp PR

    @property
    def total_input(self) -> int:
        return len(self.valid) + len(self.invalid) + len(self.pr_level_comments)

    @property
    def pass_rate(self) -> float:
        if self.total_input == 0:
            return 1.0
        return len(self.valid) / self.total_input


class FindingValidator:
    """
    Harness kiểm định và lọc findings trước khi đăng lên PR.
    """
    MAX_FINDINGS_PER_PR = 15  # Giới hạn tối đa số comment để tránh spam PR

    def __init__(self, parsed_diff: ParsedDiff | None = None):
        self._diff = parsed_diff

    def validate_single(self, finding: ReviewFinding) -> ValidationResult:
        errors: list[str] = []

        # 1. Kiểm tra tính hợp lệ cơ bản
        if not finding.file.strip():
            errors.append("Đường dẫn file không được để trống!")

        if finding.line < 1:
            errors.append(f"Số dòng phải >= 1, nhưng nhận được: {finding.line}")

        if len(finding.message) < 10:
            errors.append("Lời giải thích (message) quá ngắn (< 10 ký tự)!")

        # 2. Kiểm tra ranh giới Git Diff (Diff Boundary Check)
        if self._diff:
            is_valid, reason = self._diff.validate_finding(finding.file, finding.line)
            if not is_valid:
                errors.append(f"Diff Boundary: {reason}")

        # 3. Kiểm tra cú pháp suggestion (Tiêu chí 4 của Thầy Quí)
        if finding.suggestion:
            is_syntax_valid, syntax_err = self.validate_suggestion_syntax(finding)
            if not is_syntax_valid:
                errors.append(f"Syntax Error: {syntax_err}")

        return ValidationResult(
            finding=finding,
            is_valid=(len(errors) == 0),
            errors=errors,
        )

    def validate_suggestion_syntax(self, finding: ReviewFinding) -> tuple[bool, str]:

        if not finding.suggestion:
            return True, ""

        filepath = finding.file.lower()
        if filepath.endswith(".py"):
            import ast
            import textwrap
            try:
                clean_code = textwrap.dedent(finding.suggestion).strip()
                ast.parse(clean_code)
                return True, ""
            except SyntaxError as e:
                return False, f"Mã Python trong suggestion bị lỗi cú pháp ({e})"
        elif filepath.endswith(".json"):
            import json
            try:
                json.loads(finding.suggestion)
                return True, ""
            except Exception as e:
                return False, f"Mã JSON trong suggestion bị lỗi cú pháp ({e})"

        # Đối với các ngôn ngữ khác tạm thời chấp nhận
        return True, ""

    def validate_batch(self, findings: list[ReviewFinding]) -> BatchValidationResult:

        valid: list[ReviewFinding] = []
        invalid: list[tuple[ReviewFinding, list[str]]] = []
        pr_level: list[ReviewFinding] = []

        for finding in findings:
            result = self.validate_single(finding)

            if result.is_valid:
                valid.append(finding)
            else:
                # Kiểm tra nếu chỉ vi phạm mỗi lỗi Diff Boundary thì chuyển thành comment cấp PR
                non_boundary_errors = [e for e in result.errors if "Diff Boundary" not in e]
                if not non_boundary_errors:
                    pr_level.append(finding)
                else:
                    invalid.append((finding, result.errors))

        # Giới hạn tối đa số comment để tránh spam PR (ưu tiên critical > major > minor > nit)
        if len(valid) > self.MAX_FINDINGS_PER_PR:
            priority = {
                Severity.CRITICAL: 0,
                Severity.MAJOR: 1,
                Severity.MINOR: 2,
                Severity.NIT: 3,
            }
            valid.sort(key=lambda f: (priority.get(f.severity, 99), -f.confidence))
            valid = valid[:self.MAX_FINDINGS_PER_PR]

        return BatchValidationResult(
            valid=valid,
            invalid=invalid,
            pr_level_comments=pr_level,
        )

    def determine_verdict(self, valid_findings: list[ReviewFinding]) -> ReviewVerdict:
        """
        Tự động xác định phán quyết cho PR dựa trên danh sách finding hợp lệ:
        - Có critical hoặc major -> REQUEST_CHANGES (Chặn merge)
        - Chỉ có minor hoặc nit -> COMMENT
        - Không có lỗi nào -> APPROVE
        """
        has_critical = any(f.severity == Severity.CRITICAL for f in valid_findings)
        has_major = any(f.severity == Severity.MAJOR for f in valid_findings)

        if has_critical or has_major:
            return ReviewVerdict.REQUEST_CHANGES
        elif valid_findings:
            return ReviewVerdict.COMMENT
        else:
            return ReviewVerdict.APPROVE
