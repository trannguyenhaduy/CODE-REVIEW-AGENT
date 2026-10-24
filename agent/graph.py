"""
agent/graph.py — Bộ Não Điều Phối LangGraph (StateGraph Orchestrator)
=====================================================================
1. parse_node: Bóc tách git diff thô thành ParsedDiff (vị trí dòng có dấu +).
2. guard_node: Cổng bảo vệ token (kiểm tra diff rỗng hoặc quá giới hạn MAX_DIFF_LINES).
3. review_node: Gọi LLM (9Router / OpenAI API) để phân tích tìm bug/lỗi logic/bảo mật.
4. validate_node: Cổng an ninh FindingValidator lọc ranh giới diff, chống spam và chốt phán quyết PR.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from agent.harness.step_logger import StepLogger
from agent.harness.validator import BatchValidationResult, FindingValidator
from agent.schemas import ReviewFinding, ReviewReport, ReviewVerdict
from agent.tools.git_diff_reader import GitDiffReader, ParsedDiff

load_dotenv()


# === SYSTEM PROMPTS & TEMPLATES ===

SYSTEM_PROMPT = """Bạn là Senior Code Reviewer chuyên nghiệp, sắc bén và cẩn trọng.
Nhiệm vụ của bạn là rà soát các thay đổi mã nguồn trong Git Diff của Pull Request và phát hiện các lỗi:
- Logic & Bugs (sai thuật toán, off-by-one, đảo ngược toán tử so sánh >= thành <=, rò rỉ tài nguyên)
- Security (lộ secret, SQL injection, bypass quyền)
- Performance (vòng lặp thừa, N+1 query)
- Code Style & Maintainability

QUY TẮC CỐT LÕI (BẮT BUỘC TUÂN THỦ 100%):
1. CHỈ NHẬN XÉT CÁC DÒNG CÓ DẤU '+' (Dòng được thêm mới hoặc sửa đổi trong Git Diff).
2. Tuyệt đối KHÔNG bịa đặt số dòng hoặc tên file không có trong diff.
3. Cung cấp khối gợi ý sửa code 1-click chuẩn GitHub (suggestion) cho các lỗi quan trọng.
4. Phân loại mức độ nghiêm trọng chính xác:
   - critical: Lỗ hổng bảo mật nghiêm trọng hoặc crash hệ thống tức thì.
   - major: Lỗi logic sai nghiệp vụ (ví dụ: đảo ngược điều kiện).
   - minor: Lỗi nhỏ, xử lý thiếu ngoại lệ hiếm gặp.
   - nit: Góp ý format, đặt tên biến, comment.

ĐỊNH DẠNG ĐẦU RA (BẮT BUỘC):
Trả về DUY NHẤT một khối JSON hợp lệ theo cấu trúc sau (không kèm lời chào mở đầu hay kết thúc ngoài JSON):
```json
{
  "summary": "Tóm tắt ngắn gọn các phát hiện trong PR (1-3 câu)",
  "findings": [
    {
      "file": "đường_dẫn_file",
      "line": 43,
      "side": "RIGHT",
      "severity": "major",
      "category": "logic",
      "message": "Mô tả chi tiết nguyên nhân và hậu quả của lỗi",
      "suggestion": "dòng_code_sửa_lại_cho_đúng",
      "confidence": 0.95
    }
  ]
}
```
Nếu PR hoàn toàn sạch sẽ và không có lỗi nào, trả về danh sách "findings": [] kèm lời khen trong "summary".
"""

REVIEW_USER_PROMPT = """Vui lòng review Git Diff sau đây cho PR #{pr_number} thuộc repository '{repo}' (Commit {commit_sha}):

```diff
{diff_text}
```

Hãy tập trung kiểm tra kỹ các dòng code có dấu '+' và trả về định dạng JSON theo đúng hướng dẫn.
"""


# === STATE DEFINITION ===

class ReviewState(TypedDict, total=False):
    """Trạng thái trung tâm được truyền qua các Node trong LangGraph."""
    pr_number: int
    commit_sha: str
    repo: str
    diff_text: str
    parsed_diff: ParsedDiff | None
    raw_findings: list[dict]
    raw_summary: str
    validated_result: BatchValidationResult | None
    report: ReviewReport | None
    run_id: str
    logger: StepLogger | None
    errors: list[str]


# === HELPER: BÓC TÁCH JSON TỪ PHẢN HỒI CỦA LLM ===

def extract_json_from_response(text: str) -> dict[str, Any]:
    """Trích xuất khối JSON từ output của LLM (hỗ trợ cả raw json lẫn markdown ```json)."""
    text = text.strip()

    # Tìm khối ```json ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        json_str = match.group(1).strip()
    else:
        json_str = text

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # Fallback: tìm cặp ngoặc nhọn đầu tiên và cuối cùng
        start = json_str.find("{")
        end = json_str.rfind("}")
        if start != -1 and end != -1:
            return json.loads(json_str[start : end + 1])
        raise ValueError(f"Không thể parse JSON từ phản hồi LLM:\n{text[:300]}")


# === CÁC NODES TRONG LANGGRAPH ===

if "your-key-here" in os.getenv("LANGCHAIN_API_KEY", ""):
    os.environ["LANGCHAIN_TRACING_V2"] = "false"


def parse_node(state: ReviewState) -> dict:
    """Node 1: Bóc tách git diff thô thành ParsedDiff (tọa độ các dòng dấu +)."""
    diff_text = state.get("diff_text", "")
    logger: StepLogger | None = state.get("logger")

    if logger:
        with logger.measure_step("parse_diff", input_data={"diff_length": len(diff_text)}) as ctx:
            reader = GitDiffReader()
            parsed = reader.parse(diff_text)
            ctx.output_data = {
                "files_count": len(parsed.files),
                "changed_files": parsed.changed_file_paths,
            }
    else:
        parsed = GitDiffReader().parse(diff_text)

    return {"parsed_diff": parsed}


def guard_node(state: ReviewState) -> dict:
    """Node 2: Cổng kiểm tra an toàn (Guardrail) — chặn diff rỗng hoặc quá giới hạn token."""
    diff_text = state.get("diff_text", "").strip()
    max_lines = int(os.getenv("MAX_DIFF_LINES", "3000"))
    logger: StepLogger | None = state.get("logger")
    errors: list[str] = list(state.get("errors", []))

    if logger:
        with logger.measure_step("guard_check", input_data={"max_allowed_lines": max_lines}) as ctx:
            if not diff_text:
                err_msg = "Git Diff rỗng, không có thay đổi nào để review!"
                errors.append(err_msg)
                ctx.status = "FAILED"
                ctx.error = err_msg
            else:
                line_count = len(diff_text.splitlines())
                if line_count > max_lines:
                    err_msg = f"Git Diff vượt quá giới hạn an toàn ({line_count} > {max_lines} dòng)!"
                    errors.append(err_msg)
                    ctx.status = "FAILED"
                    ctx.error = err_msg
            ctx.output_data = {"guard_status": "PASSED" if not errors else "FAILED", "errors": errors}
    else:
        if not diff_text:
            errors.append("Git Diff rỗng, không có thay đổi nào để review!")
        elif len(diff_text.splitlines()) > max_lines:
            errors.append("Git Diff vượt quá giới hạn an toàn!")

    return {"errors": errors}


def should_continue_to_review(state: ReviewState) -> str:
    """Điều hướng có cho phép vào review_node hay nhảy thẳng sang validate_node."""
    if state.get("errors"):
        return "validate"
    return "review"


def review_node(state: ReviewState, custom_llm: Any = None) -> dict:
    """
    Node 3: Gọi AI LLM để rà soát mã nguồn và phát hiện lỗi.
    - 100% finding hợp lệ theo schema.
    - Output sai schema thì agent tự sửa tối đa 2 lần (Self-Correction Loop).
    - Quá số lần thì bỏ finding đó và ghi lỗi vào trace log.
    """
    diff_text = state.get("diff_text", "")
    pr_number = state.get("pr_number", 1)
    repo = state.get("repo", "local/repo")
    commit_sha = state.get("commit_sha", "HEAD")
    logger: StepLogger | None = state.get("logger")

    llm = custom_llm or ChatOpenAI(
        model=os.getenv("LLM_MODEL", "ag/gemini-3.8-flash-high"),
        base_url=os.getenv("OPENAI_BASE_URL", "http://localhost:20128/v1"),
        api_key=os.getenv("OPENAI_API_KEY", "not-needed"),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.0")),
    )

    sys_msg = SystemMessage(content=SYSTEM_PROMPT)
    user_msg = HumanMessage(
        content=REVIEW_USER_PROMPT.format(
            pr_number=pr_number,
            repo=repo,
            commit_sha=commit_sha,
            diff_text=diff_text,
        )
    )

    messages = [sys_msg, user_msg]
    raw_findings: list[dict] = []
    raw_summary = "Không tìm thấy lỗi đáng kể nào."
    MAX_SCHEMA_RETRIES = 2
    total_token_usage = {"prompt": 0, "completion": 0, "total": 0}

    if logger:
        with logger.measure_step("llm_review", input_data={"model": getattr(llm, "model_name", "llm")}) as ctx:
            for attempt in range(MAX_SCHEMA_RETRIES + 1):
                response = llm.invoke(messages)
                usage = getattr(response, "usage_metadata", {}) or {}
                total_token_usage["prompt"] += usage.get("input_tokens", 0)
                total_token_usage["completion"] += usage.get("output_tokens", 0)
                total_token_usage["total"] += usage.get("total_tokens", 0)

                schema_errors: list[str] = []
                valid_candidates: list[dict] = []

                try:
                    parsed_json = extract_json_from_response(response.content)
                    raw_summary = parsed_json.get("summary", raw_summary)
                    findings_candidates = parsed_json.get("findings", [])

                    for idx, item in enumerate(findings_candidates):
                        try:
                            ReviewFinding(**item)
                            valid_candidates.append(item)
                        except Exception as e:
                            schema_errors.append(f"Finding #{idx + 1} vi phạm ({e})")

                    if not schema_errors:
                        raw_findings = valid_candidates
                        break

                except Exception as e:
                    schema_errors.append(f"Lỗi cú pháp JSON ({e})")

                # Nếu sai schema và chưa quá 2 lần -> Tự động sửa lại
                if attempt < MAX_SCHEMA_RETRIES:
                    err_details = "; ".join(schema_errors)
                    logger.log_step(
                        step_name="self_correction_attempt",
                        latency_ms=0.0,
                        status="SUCCESS",
                        input_data={"attempt": attempt + 1, "errors": err_details},
                        output_data={"action": "Gửi yêu cầu LLM tự sửa schema"},
                    )
                    messages.append(response)
                    messages.append(
                        HumanMessage(
                            content=(
                                f"Output vừa rồi của bạn vi phạm schema sau:\n{err_details}\n\n"
                                f"Hãy tự sửa lại lỗi (đây là lần tự sửa #{attempt + 1}/{MAX_SCHEMA_RETRIES}) "
                                f"và trả về DUY NHẤT một khối JSON hợp lệ theo đúng schema!"
                            )
                        )
                    )
                else:
                    # Quá 2 lần: bỏ các finding vi phạm và ghi lỗi vào trace
                    logger.log_step(
                        step_name="self_correction_exhausted",
                        latency_ms=0.0,
                        status="FAILED",
                        error=f"Đã quá {MAX_SCHEMA_RETRIES} lần tự sửa. Bỏ qua các finding lỗi: {'; '.join(schema_errors)}",
                        input_data={"attempt": attempt + 1},
                        output_data={"retained_findings": len(valid_candidates)},
                    )
                    raw_findings = valid_candidates

            ctx.token_usage = total_token_usage
            ctx.output_data = {
                "raw_findings_count": len(raw_findings),
                "summary_preview": raw_summary[:100],
            }
    else:
        for attempt in range(MAX_SCHEMA_RETRIES + 1):
            response = llm.invoke(messages)
            schema_errors = []
            valid_candidates = []
            try:
                parsed_json = extract_json_from_response(response.content)
                raw_summary = parsed_json.get("summary", raw_summary)
                findings_candidates = parsed_json.get("findings", [])
                for idx, item in enumerate(findings_candidates):
                    try:
                        ReviewFinding(**item)
                        valid_candidates.append(item)
                    except Exception as e:
                        schema_errors.append(f"Finding #{idx + 1}: {e}")

                if not schema_errors:
                    raw_findings = valid_candidates
                    break
            except Exception as e:
                schema_errors.append(f"JSON error: {e}")

            if attempt < MAX_SCHEMA_RETRIES:
                messages.append(response)
                messages.append(
                    HumanMessage(
                        content=f"Output vi phạm schema: {'; '.join(schema_errors)}. Vui lòng tự sửa lại theo schema!"
                    )
                )
            else:
                raw_findings = valid_candidates

    return {"raw_findings": raw_findings, "raw_summary": raw_summary}


def validate_node(state: ReviewState) -> dict:
    """Node 4: Cổng kiểm định an toàn (FindingValidator) và đóng gói ReviewReport."""
    parsed_diff = state.get("parsed_diff")
    raw_findings_data = state.get("raw_findings", [])
    raw_summary = state.get("raw_summary", "")
    errors = state.get("errors", [])
    logger: StepLogger | None = state.get("logger")

    validator = FindingValidator(parsed_diff=parsed_diff)

    # Chuyển dict thô từ LLM thành các đối tượng ReviewFinding chuẩn Pydantic
    findings_objects: list[ReviewFinding] = []
    for item in raw_findings_data:
        try:
            findings_objects.append(ReviewFinding(**item))
        except Exception:
            # Bỏ qua finding bị hỏng schema
            continue

    if logger:
        with logger.measure_step("validate_and_verdict", input_data={"input_findings": len(findings_objects)}) as ctx:
            validated_batch = validator.validate_batch(findings_objects)
            verdict = validator.determine_verdict(validated_batch.valid)

            if errors:
                verdict = ReviewVerdict.COMMENT
                final_summary = f"Review bị gián đoạn do lỗi: {'; '.join(errors)}"
            else:
                final_summary = raw_summary or f"Review hoàn tất. Phát hiện {len(validated_batch.valid)} lỗi cần lưu ý."

            report = ReviewReport(
                pr_number=state.get("pr_number", 1),
                commit_sha=state.get("commit_sha", "HEAD"),
                verdict=verdict,
                summary=final_summary,
                findings=validated_batch.valid,
                run_id=state.get("run_id", "local_run"),
            )

            ctx.output_data = {
                "valid_count": len(validated_batch.valid),
                "pr_level_count": len(validated_batch.pr_level_comments),
                "invalid_count": len(validated_batch.invalid),
                "verdict": verdict.value,
            }
    else:
        validated_batch = validator.validate_batch(findings_objects)
        verdict = validator.determine_verdict(validated_batch.valid)
        final_summary = raw_summary or f"Review hoàn tất. Phát hiện {len(validated_batch.valid)} lỗi."
        report = ReviewReport(
            pr_number=state.get("pr_number", 1),
            commit_sha=state.get("commit_sha", "HEAD"),
            verdict=verdict,
            summary=final_summary,
            findings=validated_batch.valid,
            run_id=state.get("run_id", "local_run"),
        )

    return {
        "validated_result": validated_batch,
        "report": report,
    }


# === KHỞI TẠO STATEGRAPH ===

def create_review_graph(custom_llm: Any = None) -> Any:
    """Xây dựng và biên dịch LangGraph StateGraph hoàn chỉnh."""
    workflow = StateGraph(ReviewState)

    # Đăng ký các Nodes
    workflow.add_node("parse", parse_node)
    workflow.add_node("guard", guard_node)
    workflow.add_node("review", lambda state: review_node(state, custom_llm=custom_llm))
    workflow.add_node("validate", validate_node)

    # Đấu nối các Edges
    workflow.add_edge(START, "parse")
    workflow.add_edge("parse", "guard")
    workflow.add_conditional_edges(
        "guard",
        should_continue_to_review,
        {
            "review": "review",
            "validate": "validate",
        },
    )
    workflow.add_edge("review", "validate")
    workflow.add_edge("validate", END)

    return workflow.compile()


def run_code_review(
    diff_text: str,
    pr_number: int = 1,
    commit_sha: str = "HEAD",
    repo: str = "local/repo",
    custom_llm: Any = None,
    logger: StepLogger | None = None,
) -> ReviewReport:
    """
    Hàm entry point tiện lợi chạy toàn bộ quy trình review và trả về ReviewReport.
    """
    app = create_review_graph(custom_llm=custom_llm)
    run_id = logger.run_id if logger else "run_standalone"

    initial_state: ReviewState = {
        "pr_number": pr_number,
        "commit_sha": commit_sha,
        "repo": repo,
        "diff_text": diff_text,
        "run_id": run_id,
        "logger": logger,
        "errors": [],
    }

    final_state = app.invoke(initial_state)
    return final_state["report"]
