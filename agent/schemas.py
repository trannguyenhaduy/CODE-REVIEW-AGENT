"""
agent/schemas.py — (Structured Output Schema)
========================================================================
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

# ─────────────────────────────────────────────────────────────
# 1. Các kiểu dữ liệu liệt kê (Enums)
# ─────────────────────────────────────────────────────────────

class Severity(str, Enum):

    CRITICAL = "critical"   # Lỗ hổng bảo mật nghiêm trọng, crash hệ thống -> Chặn merge PR
    MAJOR    = "major"      # Lỗi logic nghiệp vụ, memory leak, truy vấn N+1
    MINOR    = "minor"      # Thiếu validation, thiếu edge case nhỏ
    NIT      = "nit"        # Format code, typo cú pháp -> Không chặn merge


class Category(str, Enum):

    LOGIC       = "logic"        # Lỗi thuật toán, sai điều kiện, off-by-one
    SECURITY    = "security"     # SQL Injection, lộ secret, thiếu xác thực
    PERFORMANCE = "performance"  # Truy vấn N+1, vòng lặp thừa, tốn bộ nhớ
    CONVENTION  = "convention"   # Vi phạm quy ước nhóm CONVENTIONS.md
    TEST        = "test"         # Thiếu test case cho code mới
    OTHER       = "other"        # Các vấn đề khác


class DiffSide(str, Enum):

    RIGHT = "RIGHT"  # Dòng mới thêm vào (có dấu + trong diff)
    LEFT  = "LEFT"   # Dòng bị xóa đi (có dấu - trong diff)


class ReviewVerdict(str, Enum):

    APPROVE          = "approve"          # Code sạch hoặc chỉ có góp ý nhỏ -> Cho merge
    COMMENT          = "comment"          # Nhận xét cần lưu ý, không chặn merge
    REQUEST_CHANGES  = "request_changes"  # Có lỗi critical/major -> Chặn merge bắt buộc sửa


# ─────────────────────────────────────────────────────────────
# 2. Schema cho một nhận xét đơn lẻ (ReviewFinding)
# ─────────────────────────────────────────────────────────────

class ReviewFinding(BaseModel):

    file: str = Field(
        description="Đường dẫn tương đối của file bị lỗi (phải có trong diff)"
    )
    line: int = Field(
        ge=1,
        description="Số dòng ở phiên bản mới (HEAD), phải nằm trong một hunk của diff"
    )
    side: DiffSide = Field(
        default=DiffSide.RIGHT,
        description="RIGHT = dòng mới (+); LEFT = dòng bị xóa (-)"
    )
    severity: Severity = Field(
        description="Mức độ nghiêm trọng: critical / major / minor / nit"
    )
    category: Category = Field(
        description="Phân loại lỗi: logic / security / performance / convention / test / other"
    )
    message: str = Field(
        min_length=10,
        description="Giải thích ngắn gọn: vấn đề là gì, tại sao sai (tối thiểu 10 ký tự)"
    )
    suggestion: str | None = Field(
        default=None,
        description="Đoạn code sửa thay thế 1-click chuẩn GitHub suggestion (nếu có)"
    )
    confidence: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Độ tin cậy của finding từ 0.0 đến 1.0"
    )
    rule_ref: str | None = Field(
        default=None,
        description="Mã quy tắc từ CONVENTIONS.md (dùng cho UC-02, ví dụ: CONV-012)"
    )
    tool_source: str | None = Field(
        default=None,
        description="Công cụ phân tích tĩnh phát hiện (dùng cho UC-03, ví dụ: ruff:E711, bandit:B608)"
    )

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_lower = v.lower().strip()
            aliases = {
                "bug": "logic",
                "style": "convention",
                "docs": "other",
                "documentation": "other",
                "architecture": "other",
            }
            return aliases.get(v_lower, v_lower)
        return v

    @field_validator("severity", mode="before")
    @classmethod
    def normalize_severity(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.lower().strip()
        return v

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Lời nhắn nhận xét (message) không được rỗng!")
        return v.strip()


# ─────────────────────────────────────────────────────────────
# 3. Schema cho Báo Cáo Tổng Hợp Review (ReviewReport)
# ─────────────────────────────────────────────────────────────

class ReviewReport(BaseModel):
    pr_number: int = Field(description="Số hiệu Pull Request")
    commit_sha: str = Field(description="Mã commit SHA được review")
    verdict: ReviewVerdict = Field(description="Phán quyết: approve / comment / request_changes")
    summary: str = Field(description="Tóm tắt ngắn gọn các phát hiện trong PR")
    findings: list[ReviewFinding] = Field(
        default_factory=list,
        description="Danh sách các findings đã được kiểm định hợp lệ"
    )
    run_id: str = Field(description="ID định danh lần chạy review này để phục vụ lưu vết trace log")
