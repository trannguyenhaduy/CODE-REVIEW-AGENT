"""
agent/harness/validator.py — Validator Harness
===============================================
Kiểm tra tính hợp lệ của findings TRƯỚC khi đăng lên PR.
Đây là lớp harness bảo vệ quan trọng nhất — chống hallucination.

Theo yêu cầu UC-01:
1. 100% finding hợp lệ theo schema
2. 100% finding đăng lên có file/line nằm trong diff
3. Finding trỏ ra ngoài diff bị validator loại hoặc chuyển thành comment cấp PR
4. Agent tự sửa tối đa 2 lần nếu output sai schema
"""
from __future__ import annotations

import re
from typing import Optional
from dataclasses import dataclass, field

from agent.schemas import ReviewFinding, Severity, Category


@dataclass
class ValidationResult:
    """Kết quả validate một finding."""
    finding: ReviewFinding
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    
    def __str__(self) -> str:
        status = "✅ VALID" if self.is_valid else "❌ INVALID"
        if self.errors:
            return f"{status}: {'; '.join(self.errors)}"
        return status


@dataclass
class BatchValidationResult:
    """Kết quả validate cả batch findings."""
    valid: list[ReviewFinding]
    invalid: list[tuple[ReviewFinding, list[str]]]
    pr_level_comments: list[ReviewFinding]  # Finding hợp lệ nhưng line out-of-diff → comment cấp PR
    
    @property
    def total_input(self) -> int:
        return len(self.valid) + len(self.invalid) + len(self.pr_level_comments)
    
    @property
    def pass_rate(self) -> float:
        if self.total_input == 0:
            return 1.0
        return len(self.valid) / self.total_input
    
    def summary(self) -> str:
        return (
            f"Input: {self.total_input} | "
            f"Valid: {len(self.valid)} | "
            f"Invalid: {len(self.invalid)} | "
            f"PR-level: {len(self.pr_level_comments)} | "
            f"Pass rate: {self.pass_rate:.1%}"
        )


class FindingValidator:
    """
    Validator harness cho ReviewFinding.
    
    Sử dụng:
        from agent.tools.git_diff_reader import GitDiffReader
        
        reader = GitDiffReader()
        parsed = reader.parse(diff_text)
        
        validator = FindingValidator(parsed_diff=parsed)
        result = validator.validate_batch(findings)
        
        # Chỉ đăng finding hợp lệ
        safe_findings = result.valid
    """
    
    # Giới hạn tối đa finding đăng lên PR (thêm vào summary nếu vượt)
    MAX_FINDINGS_PER_PR = 15
    MAX_MAJOR_ON_CLEAN_PR = 2  # PR sạch không nên có quá 2 major findings
    
    def __init__(self, parsed_diff=None, conventions_codes: Optional[set[str]] = None):
        """
        Args:
            parsed_diff: ParsedDiff từ GitDiffReader (để validate file/line)
            conventions_codes: Tập mã quy tắc hợp lệ từ CONVENTIONS.md
        """
        self._diff = parsed_diff
        self._conventions_codes = conventions_codes or set()
    
    def validate_single(self, finding: ReviewFinding) -> ValidationResult:
        """Validate một finding đơn lẻ."""
        errors = []
        
        # 1. Schema validation (Pydantic đã làm, nhưng kiểm tra thêm)
        if not finding.file.strip():
            errors.append("file không được rỗng")
        
        if finding.line < 1:
            errors.append(f"line phải >= 1, got {finding.line}")
        
        if finding.confidence < 0 or finding.confidence > 1:
            errors.append(f"confidence phải trong [0, 1], got {finding.confidence}")
        
        if len(finding.message) < 10:
            errors.append("message quá ngắn (< 10 ký tự)")
        
        # 2. Diff boundary validation
        if self._diff:
            is_valid, reason = self._diff.validate_finding(finding.file, finding.line)
            if not is_valid:
                errors.append(f"Diff boundary: {reason}")
        
        # 3. Convention citation validation  
        if finding.category == Category.CONVENTION and finding.rule_ref:
            if self._conventions_codes and finding.rule_ref not in self._conventions_codes:
                errors.append(
                    f"Mã quy tắc '{finding.rule_ref}' không tồn tại trong CONVENTIONS.md"
                )
        
        # 4. Suggestion syntax check (basic)
        if finding.suggestion:
            if len(finding.suggestion) > 5000:
                errors.append("suggestion quá dài (> 5000 ký tự)")
        
        return ValidationResult(
            finding=finding,
            is_valid=len(errors) == 0,
            errors=errors,
        )
    
    def validate_batch(
        self, 
        findings: list[ReviewFinding],
        max_retries: int = 2,
    ) -> BatchValidationResult:
        """
        Validate cả batch findings.
        Finding không hợp lệ do schema → reject.
        Finding hợp lệ nhưng line out-of-diff → chuyển thành PR-level comment.
        
        Args:
            findings: Danh sách findings từ agent
            max_retries: Không dùng ở đây nhưng track để báo cáo
        """
        valid: list[ReviewFinding] = []
        invalid: list[tuple[ReviewFinding, list[str]]] = []
        pr_level: list[ReviewFinding] = []
        
        for finding in findings:
            result = self.validate_single(finding)
            
            if result.is_valid:
                valid.append(finding)
            else:
                # Kiểm tra nếu chỉ lỗi diff boundary → downgrade thành PR-level
                non_boundary_errors = [
                    e for e in result.errors 
                    if "Diff boundary" not in e
                ]
                if not non_boundary_errors:
                    # Chỉ lỗi boundary → PR-level comment
                    pr_level.append(finding)
                else:
                    invalid.append((finding, result.errors))
        
        # Giới hạn tổng findings
        if len(valid) > self.MAX_FINDINGS_PER_PR:
            # Ưu tiên: critical > major > minor > nit
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
    
    def check_suggestion_applicable(self, finding: ReviewFinding, file_content: str) -> bool:
        """
        Kiểm tra suggestion có thể áp dụng vào file không.
        Kiểm tra đơn giản: dòng bị thay thế có tồn tại không.
        """
        if not finding.suggestion:
            return True  # Không có suggestion thì không cần check
        
        lines = file_content.splitlines()
        if finding.line - 1 >= len(lines):
            return False
        
        return True  # Basic check pass; full check dùng git apply --check
    
    def dedup_findings(self, findings: list[ReviewFinding]) -> list[ReviewFinding]:
        """
        Loại bỏ findings trùng lặp (cùng file + chồng dòng + cùng category).
        Dùng sau aggregator trong UC-04.
        """
        seen: dict[tuple, ReviewFinding] = {}
        
        for f in findings:
            key = (f.file, f.line, f.category)
            if key not in seen:
                seen[key] = f
            else:
                # Giữ finding có severity cao hơn
                existing = seen[key]
                priority = {Severity.CRITICAL: 0, Severity.MAJOR: 1, 
                           Severity.MINOR: 2, Severity.NIT: 3}
                if priority.get(f.severity, 99) < priority.get(existing.severity, 99):
                    seen[key] = f
        
        return list(seen.values())
