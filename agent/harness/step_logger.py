"""
agent/harness/step_logger.py — Step Logging Harness
====================================================
Ghi vết chi tiết từng vòng lặp của agent theo yêu cầu Phase 1:
- Step number, Timestamp
- Thought (suy luận của LLM)
- Tool Call (tên tool + tham số)
- Observation (kết quả tool)
- Token usage (prompt + completion)
- Latency (ms)
- Findings sinh ra trong step này

Output: JSONL file + in ra console (Rich format)

Theo rubric: Trace phải thể hiện từng vòng: hunk đang xét → tool đã gọi → finding sinh ra
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich import print as rprint
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


# ─────────────────────────────────────────────────────────────
# Data Structures
# ─────────────────────────────────────────────────────────────

@dataclass
class StepRecord:
    """Một bước trong vòng lặp agent."""
    step_index: int
    run_id: str
    pr_number: int
    commit_sha: str
    timestamp_utc: str
    
    # ReAct pattern components
    thought: str = ""
    tool_name: Optional[str] = None
    tool_args: dict = field(default_factory=dict)
    observation: str = ""
    
    # Findings trong step này
    findings_generated: list[dict] = field(default_factory=list)
    
    # Performance metrics
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_usd: float = 0.0
    
    # Status
    error: Optional[str] = None
    is_final_step: bool = False
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RunSummary:
    """Tóm tắt toàn bộ một lần run agent."""
    run_id: str
    pr_number: int
    commit_sha: str
    repo: str
    started_at: str
    finished_at: str = ""
    total_steps: int = 0
    total_tool_calls: int = 0
    total_findings: int = 0
    verdict: str = "unknown"
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    total_latency_ms: float = 0.0
    errors: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return asdict(self)


# ─────────────────────────────────────────────────────────────
# Step Logger
# ─────────────────────────────────────────────────────────────

class StepLogger:
    """
    Ghi log chi tiết từng bước của agent.
    
    Sử dụng:
        logger = StepLogger(pr_number=42, commit_sha="abc123", repo="owner/repo")
        
        # Trong mỗi step của agent:
        with logger.step() as step:
            step.thought = "Tôi cần đọc file booking.py để hiểu context"
            step.tool_name = "read_file_at_ref"
            step.tool_args = {"path": "app/booking.py", "start_line": 40}
            step.observation = "... nội dung file ..."
            step.prompt_tokens = 1200
            step.completion_tokens = 300
        
        logger.finalize(verdict="request_changes", findings=all_findings)
    """
    
    # Giá ước tính theo model (USD per 1M tokens) - chỉ để estimate
    TOKEN_COST = {
        "gpt-4o": {"prompt": 2.5, "completion": 10.0},
        "gpt-4o-mini": {"prompt": 0.15, "completion": 0.6},
        "gpt-4-turbo": {"prompt": 10.0, "completion": 30.0},
        "claude-3-5-sonnet": {"prompt": 3.0, "completion": 15.0},
        "default": {"prompt": 1.0, "completion": 3.0},
    }
    
    def __init__(
        self,
        pr_number: int,
        commit_sha: str,
        repo: str,
        log_dir: str | Path = "./logs",
        model: str = "default",
        console_output: bool = True,
    ):
        self.pr_number = pr_number
        self.commit_sha = commit_sha[:8]  # Short SHA
        self.repo = repo
        self.model = model
        self.console_output = console_output and RICH_AVAILABLE
        
        # Generate run ID
        self.run_id = f"PR{pr_number}_{self.commit_sha}_{uuid.uuid4().hex[:6]}"
        
        # Setup log directory
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Log file paths
        self.trace_file = self.log_dir / f"trace_{self.run_id}.jsonl"
        self.summary_file = self.log_dir / f"summary_{self.run_id}.json"
        
        # State
        self._steps: list[StepRecord] = []
        self._step_counter = 0
        self._run_start = time.monotonic()
        self._started_at = datetime.now(timezone.utc).isoformat()
        
        if self.console_output:
            self._console = Console()
        
        # Write header comment to trace file
        self._write_to_trace({"event": "run_start", "run_id": self.run_id, 
                               "pr": pr_number, "sha": self.commit_sha, "repo": repo})
    
    def _estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Ước tính chi phí dựa trên model."""
        pricing = self.TOKEN_COST.get(self.model, self.TOKEN_COST["default"])
        return (
            prompt_tokens / 1_000_000 * pricing["prompt"] + 
            completion_tokens / 1_000_000 * pricing["completion"]
        )
    
    def _write_to_trace(self, data: dict) -> None:
        """Append một record vào JSONL trace file."""
        try:
            with open(self.trace_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False, default=str) + "\n")
        except Exception as e:
            print(f"[StepLogger] Không ghi được trace: {e}")
    
    def log_step(
        self,
        thought: str = "",
        tool_name: Optional[str] = None,
        tool_args: Optional[dict] = None,
        observation: str = "",
        findings: Optional[list] = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        latency_ms: float = 0.0,
        error: Optional[str] = None,
        is_final: bool = False,
    ) -> StepRecord:
        """
        Ghi log một step đầy đủ.
        Đây là method chính để gọi sau mỗi vòng lặp agent.
        """
        self._step_counter += 1
        cost = self._estimate_cost(prompt_tokens, completion_tokens)
        
        step = StepRecord(
            step_index=self._step_counter,
            run_id=self.run_id,
            pr_number=self.pr_number,
            commit_sha=self.commit_sha,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            thought=thought,
            tool_name=tool_name,
            tool_args=tool_args or {},
            observation=observation[:2000] if observation else "",  # Truncate large observations
            findings_generated=[
                f if isinstance(f, dict) else f.model_dump() 
                for f in (findings or [])
            ],
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_cost_usd=cost,
            error=error,
            is_final_step=is_final,
        )
        
        self._steps.append(step)
        self._write_to_trace(step.to_dict())
        
        # Console output
        if self.console_output:
            self._print_step(step)
        
        return step
    
    def _print_step(self, step: StepRecord) -> None:
        """In step ra console với Rich formatting."""
        console = self._console
        
        header = f"[bold blue]Step {step.step_index}[/] · {step.timestamp_utc[11:19]}"
        if step.tool_name:
            header += f" · 🔧 [yellow]{step.tool_name}[/]"
        if step.error:
            header += f" · [red]ERROR[/]"
        
        lines = []
        if step.thought:
            lines.append(f"[dim]💭 Thought:[/dim] {step.thought[:200]}")
        if step.tool_name:
            args_preview = str(step.tool_args)[:100]
            lines.append(f"[dim]🔧 Tool:[/dim] {step.tool_name}({args_preview})")
        if step.observation:
            obs_preview = step.observation[:300].replace("\n", " ")
            lines.append(f"[dim]👁 Observation:[/dim] {obs_preview}")
        if step.findings_generated:
            lines.append(f"[dim]🎯 Findings:[/dim] [green]+{len(step.findings_generated)} finding(s)[/]")
        if step.error:
            lines.append(f"[red]❌ Error:[/red] {step.error}")
        
        metrics = (
            f"[dim]tokens: {step.prompt_tokens}+{step.completion_tokens} "
            f"| cost: ${step.estimated_cost_usd:.4f} "
            f"| {step.latency_ms:.0f}ms[/dim]"
        )
        lines.append(metrics)
        
        console.print(Panel("\n".join(lines), title=header, expand=False))
    
    def finalize(
        self, 
        verdict: str = "comment",
        findings: Optional[list] = None,
    ) -> RunSummary:
        """
        Kết thúc run, tổng hợp stats và ghi summary.
        
        Args:
            verdict: Kết luận cuối: "approve", "comment", "request_changes"
            findings: Danh sách findings cuối cùng
        """
        total_prompt = sum(s.prompt_tokens for s in self._steps)
        total_completion = sum(s.completion_tokens for s in self._steps)
        total_cost = sum(s.estimated_cost_usd for s in self._steps)
        tool_calls = sum(1 for s in self._steps if s.tool_name)
        errors = [s.error for s in self._steps if s.error]
        
        elapsed_ms = (time.monotonic() - self._run_start) * 1000
        
        summary = RunSummary(
            run_id=self.run_id,
            pr_number=self.pr_number,
            commit_sha=self.commit_sha,
            repo=self.repo,
            started_at=self._started_at,
            finished_at=datetime.now(timezone.utc).isoformat(),
            total_steps=self._step_counter,
            total_tool_calls=tool_calls,
            total_findings=len(findings) if findings else 0,
            verdict=verdict,
            total_tokens=total_prompt + total_completion,
            total_cost_usd=round(total_cost, 6),
            total_latency_ms=round(elapsed_ms, 2),
            errors=errors,
        )
        
        # Ghi summary JSON
        try:
            with open(self.summary_file, "w", encoding="utf-8") as f:
                json.dump(summary.to_dict(), f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            print(f"[StepLogger] Không ghi được summary: {e}")
        
        self._write_to_trace({"event": "run_end", **summary.to_dict()})
        
        # Console summary
        if self.console_output:
            self._print_summary(summary)
        
        return summary
    
    def _print_summary(self, summary: RunSummary) -> None:
        """In tóm tắt run ra console."""
        verdict_color = {
            "approve": "green",
            "comment": "yellow",
            "request_changes": "red",
        }.get(summary.verdict, "white")
        
        self._console.print(Panel(
            f"[bold]Run ID:[/] {summary.run_id}\n"
            f"[bold]PR:[/] #{summary.pr_number} @ {summary.commit_sha}\n"
            f"[bold]Verdict:[/] [{verdict_color}]{summary.verdict.upper()}[/]\n"
            f"[bold]Steps:[/] {summary.total_steps} | "
            f"[bold]Tool Calls:[/] {summary.total_tool_calls} | "
            f"[bold]Findings:[/] {summary.total_findings}\n"
            f"[bold]Tokens:[/] {summary.total_tokens:,} | "
            f"[bold]Cost:[/] ${summary.total_cost_usd:.4f} | "
            f"[bold]Time:[/] {summary.total_latency_ms/1000:.1f}s\n"
            + (f"[red]Errors: {len(summary.errors)}[/]" if summary.errors else "[green]No errors[/]"),
            title=f"[bold]📊 Run Summary — {summary.run_id}[/]",
            border_style=verdict_color,
        ))
    
    @property
    def trace_path(self) -> str:
        """Đường dẫn file trace JSONL."""
        return str(self.trace_file)
