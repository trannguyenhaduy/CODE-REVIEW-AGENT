"""
agent/schemas.py — Pydantic v2 Structured Output Schemas
=========================================================
Tất cả schema đầu vào/đầu ra của agent được định nghĩa tập trung ở đây.
Agent bắt buộc dùng schema này — KHÔNG được để LLM trả về plain text.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


# ─────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────

class Severity(str, Enum):
    """Mức độ nghiêm trọng của finding — chuẩn theo đề tài."""
    CRITICAL = "critical"   # Lỗ hổng bảo mật, crash hệ thống → block merge
    MAJOR    = "major"      # Lỗi logic, memory leak, N+1 query
    MINOR    = "minor"      # Thiếu validation, thiếu edge case
    NIT      = "nit"        # Format, typo — không chặn merge


class Category(str, Enum):
    """Phân loại lỗi theo rubric đề tài."""
    LOGIC       = "logic"
    SECURITY    = "security"
    PERFORMANCE = "performance"
    CONVENTION  = "convention"
    TEST        = "test"
    OTHER       = "other"


class DiffSide(str, Enum):
    """Phía của dòng trong git diff."""
    RIGHT = "RIGHT"  # Dòng mới (thêm vào)
    LEFT  = "LEFT"   # Dòng bị xóa


class ReviewVerdict(str, Enum):
    """Kết luận tổng thể của review."""
    APPROVE          = "approve"
    COMMENT          = "comment"
    REQUEST_CHANGES  = "request_changes"


# ─────────────────────────────────────────────────────────────
# Core Finding Schema (UC-01, UC-03, UC-04)
# ─────────────────────────────────────────────────────────────

class ReviewFinding(BaseModel):
    """
    Một finding đơn lẻ gắn vào một dòng cụ thể trong diff.
    
    Bất biến quan trọng (kiểm tra bởi Validator Harness):
    - `file` PHẢI thuộc danh sách file có trong diff
    - `line` PHẢI nằm trong một hunk hợp lệ của diff
    - `suggestion` nếu có PHẢI áp được bằng git apply --check
    """
    file: str = Field(
        description="Đường dẫn file tương đối từ gốc repo, phải có trong diff"
    )
    line: int = Field(
        ge=1,
        description="Số dòng trong phiên bản HEAD (phải nằm trong hunk của diff)"
    )
    side: DiffSide = Field(
        default=DiffSide.RIGHT,
        description="RIGHT = dòng mới (thêm); LEFT = dòng bị xóa"
    )
    severity: Severity = Field(
        description="Mức độ nghiêm trọng: critical/major/minor/nit"
    )
    category: Category = Field(
        description="Phân loại: logic/security/performance/convention/test/other"
    )
    message: str = Field(
        min_length=10,
        max_length=500,
        description="Giải thích ngắn: vấn đề là gì, tại sao sai"
    )
    suggestion: Optional[str] = Field(
        default=None,
        description="Đoạn code thay thế cho đúng dòng bị nhận xét (GitHub suggestion format)"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Độ tin cậy của finding (0.0-1.0)"
    )
    rule_ref: Optional[str] = Field(
        default=None,
        description="Mã quy tắc từ CONVENTIONS.md nếu là lỗi convention (ví dụ: CONV-012)"
    )
    tool_source: Optional[str] = Field(
        default=None,
        description="Công cụ phân tích tĩnh sinh ra finding này (ví dụ: ruff:E711, bandit:B602)"
    )

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("message không được rỗng")
        return v.strip()


# ─────────────────────────────────────────────────────────────
# Review Report Schema (UC-04 Aggregator output)
# ─────────────────────────────────────────────────────────────

class ReviewReport(BaseModel):
    """
    Kết quả tổng hợp review của toàn bộ PR.
    Đây là output cuối cùng sau bước Aggregator (UC-04).
    """
    pr_number: int = Field(description="Số PR trên GitHub/Bitbucket")
    commit_sha: str = Field(description="Commit SHA của HEAD được review")
    verdict: ReviewVerdict = Field(
        description="Kết luận: approve/comment/request_changes"
    )
    summary: str = Field(
        max_length=1000,
        description="Tóm tắt review ngắn gọn cho tác giả PR"
    )
    findings: list[ReviewFinding] = Field(
        default_factory=list,
        description="Danh sách findings sau khi dedup và filter"
    )
    total_findings_before_filter: int = Field(
        default=0,
        description="Tổng findings trước khi dedup (để đo hiệu quả aggregator)"
    )
    run_id: str = Field(description="ID của lần review này (PR_number + commit_sha prefix)")
    token_usage: dict = Field(
        default_factory=dict,
        description="{'prompt_tokens': int, 'completion_tokens': int, 'total_cost_usd': float}"
    )

    @field_validator("findings")
    @classmethod
    def max_findings_limit(cls, v: list[ReviewFinding]) -> list[ReviewFinding]:
        """Giới hạn tối đa 15 findings đăng lên PR (phần còn lại vào summary)."""
        return v[:15]


# ─────────────────────────────────────────────────────────────
# PR Assessment Schema (UC-06)
# ─────────────────────────────────────────────────────────────

class RiskLevel(str, Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"


class RiskFactor(BaseModel):
    factor: str = Field(description="Mô tả yếu tố rủi ro")
    evidence: str = Field(description="Bằng chứng cụ thể từ diff hoặc tài liệu")
    source: str = Field(description="File hoặc tài liệu làm căn cứ")


class PRAssessment(BaseModel):
    """Output của UC-06: Tóm tắt PR và đánh giá rủi ro."""
    summary: str = Field(
        max_length=800,
        description="PR làm gì, ≤ 120 từ"
    )
    changes: list[dict] = Field(
        description="[{area, description, files}] — mỗi vùng thay đổi"
    )
    risk_level: RiskLevel
    risk_factors: list[RiskFactor] = Field(default_factory=list)
    review_focus: list[str] = Field(
        default_factory=list,
        description="Những chỗ người review nên xem kỹ"
    )
    mismatch: list[str] = Field(
        default_factory=list,
        description="Điểm mô tả PR không khớp với diff"
    )


# ─────────────────────────────────────────────────────────────
# Thread Reply Schema (UC-10)
# ─────────────────────────────────────────────────────────────

class ThreadDecision(str, Enum):
    RESOLVE    = "resolve"    # Lỗi đã được sửa
    KEEP_OPEN  = "keep_open"  # Lỗi chưa sửa, giữ thread
    CLARIFY    = "clarify"    # Cần giải thích thêm


class ThreadReply(BaseModel):
    """Output của UC-10: Phản hồi trong review thread."""
    thread_id: str
    decision: ThreadDecision
    message: str = Field(max_length=500)
    evidence: Optional[str] = Field(
        default=None,
        description="Dòng code hiện tại làm bằng chứng (nếu keep_open)"
    )


# ─────────────────────────────────────────────────────────────
# Agent State Schema (LangGraph)
# ─────────────────────────────────────────────────────────────

class AgentState(BaseModel):
    """
    State của LangGraph workflow — được serialize vào SQLite checkpoint.
    Dùng TypedDict trong practice nhưng Pydantic model để documentation rõ hơn.
    """
    pr_number: int
    repo_full_name: str  # "owner/repo"
    commit_sha: str
    diff_text: str = Field(default="", description="Raw diff text")
    
    # Tools results
    changed_files: list[str] = Field(default_factory=list)
    file_contexts: dict[str, str] = Field(default_factory=dict)
    
    # Review progress
    findings: list[ReviewFinding] = Field(default_factory=list)
    verdict: Optional[ReviewVerdict] = None
    
    # Tracking
    tool_calls_count: int = Field(default=0)
    current_step: str = Field(default="init")
    error_log: list[str] = Field(default_factory=list)
    
    # Phase 2+
    memory_hits: list[dict] = Field(default_factory=list)
    chunk_state: dict = Field(default_factory=dict)  # UC-05
