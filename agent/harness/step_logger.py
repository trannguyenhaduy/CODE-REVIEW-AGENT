"""
agent/harness/step_logger.py — Hộp Đen Ghi Vết Kiểm Toán (Audit Step Logger)
=============================================================================
Theo tiêu chuẩn SE373 (Mảng K7: Observability / Khả năng quan sát)
và mục 3.2 dòng 225 - 230 đề tài Code Review Agent:
- Ghi vết mọi bước chạy (Parse, Guard, Review, Validate, Report) thành định dạng JSONL.
- Đo đạc chính xác thời gian thực thi (latency_ms) và token tiêu thụ.
- Đảm bảo tính minh bạch, có thể tái lập (Reproducibility) và truy vết nguyên nhân khi AI gặp lỗi.
"""
from __future__ import annotations

import json
import time
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class StepRecord:
    """Bản ghi chi tiết cho một bước chạy của Agent."""
    run_id: str
    step_index: int
    step_name: str
    timestamp: str
    latency_ms: float
    status: str = "SUCCESS"  # SUCCESS hoặc FAILED
    input_data: Any = None
    output_data: Any = None
    token_usage: dict[str, int] = field(default_factory=lambda: {"prompt": 0, "completion": 0, "total": 0})
    error: str | None = None

    def to_json_line(self) -> str:
        """Chuyển bản ghi thành 1 dòng JSON hoàn chỉnh."""
        return json.dumps(asdict(self), ensure_ascii=False)


class StepContext:
    """Đối tượng phụ trợ trong context manager để cập nhật output/tokens sau khi bước chạy xong."""
    def __init__(self, step_name: str, input_data: Any = None):
        self.step_name = step_name
        self.input_data = input_data
        self.output_data: Any = None
        self.token_usage: dict[str, int] = {"prompt": 0, "completion": 0, "total": 0}
        self.status: str = "SUCCESS"
        self.error: str | None = None


class StepLogger:
    """
    Quản lý ghi vết audit log dạng JSONL cho một phiên chạy (run_id).
    Hỗ trợ cả ghi log trực tiếp lẫn context manager đo lường tự động.
    """
    def __init__(self, run_id: str | None = None, log_dir: str = "logs"):
        self.run_id = run_id or f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / f"{self.run_id}.jsonl"

        self._step_counter = 0
        self.records: list[StepRecord] = []

    def log_step(
        self,
        step_name: str,
        latency_ms: float,
        input_data: Any = None,
        output_data: Any = None,
        token_usage: dict[str, int] | None = None,
        status: str = "SUCCESS",
        error: str | None = None,
    ) -> StepRecord:
        """Ghi nhận trực tiếp một bước chạy vào bộ nhớ và file JSONL."""
        record = StepRecord(
            run_id=self.run_id,
            step_index=self._step_counter,
            step_name=step_name,
            timestamp=datetime.now(UTC).isoformat(),
            latency_ms=round(latency_ms, 2),
            status=status,
            input_data=input_data,
            output_data=output_data,
            token_usage=token_usage or {"prompt": 0, "completion": 0, "total": 0},
            error=error,
        )
        self._step_counter += 1
        self.records.append(record)

        # Ghi ngay lập tức xuống đĩa (flush để chống mất dữ liệu khi crash)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(record.to_json_line() + "\n")

        return record

    @contextmanager
    def measure_step(self, step_name: str, input_data: Any = None) -> Generator[StepContext, None, None]:

        ctx = StepContext(step_name=step_name, input_data=input_data)
        start_time = time.perf_counter()
        try:
            yield ctx
        except Exception as e:
            ctx.status = "FAILED"
            ctx.error = str(e)
            raise
        finally:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            self.log_step(
                step_name=ctx.step_name,
                latency_ms=latency_ms,
                input_data=ctx.input_data,
                output_data=ctx.output_data,
                token_usage=ctx.token_usage,
                status=ctx.status,
                error=ctx.error,
            )

    def get_summary(self) -> dict[str, Any]:
        """Thống kê tổng quan phiên chạy: tổng thời gian, tổng token, số bước thành công/thất bại."""
        total_latency = sum(r.latency_ms for r in self.records)
        total_prompt_tokens = sum(r.token_usage.get("prompt", 0) for r in self.records)
        total_completion_tokens = sum(r.token_usage.get("completion", 0) for r in self.records)
        total_tokens = sum(r.token_usage.get("total", 0) for r in self.records)
        failed_steps = [r.step_name for r in self.records if r.status == "FAILED"]

        return {
            "run_id": self.run_id,
            "total_steps": len(self.records),
            "total_latency_ms": round(total_latency, 2),
            "token_usage": {
                "prompt": total_prompt_tokens,
                "completion": total_completion_tokens,
                "total": total_tokens,
            },
            "status": "FAILED" if failed_steps else "SUCCESS",
            "failed_steps": failed_steps,
        }

    def read_records(self) -> list[dict[str, Any]]:
        """Đọc lại toàn bộ bản ghi từ file JSONL trên đĩa."""
        if not self.log_file.exists():
            return []
        records = []
        with open(self.log_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records
