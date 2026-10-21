"""
agent/graph.py — LangGraph ReAct Workflow cho Code Review Agent (UC-01)
=======================================================================
Kiến trúc LangGraph StateGraph với các node:

    fetch_pr → guard → plan → review_loop → validate → verify → publish

Mỗi node tương ứng với một lớp harness theo 12 lớp harness của môn học SE373.
"""
from __future__ import annotations

import os
import time
from typing import Annotated, Optional, TypedDict

from dotenv import load_dotenv
load_dotenv()

# Tắt LangSmith tracing nếu chưa có key thật để tránh lỗi HTTP 403
if not os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGCHAIN_API_KEY", "").startswith("ls__..."):
    os.environ["LANGCHAIN_TRACING_V2"] = "false"

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None  # type: ignore

try:
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
    from langchain_core.tools import BaseTool
    from langgraph.graph import StateGraph, END, START
    from langgraph.prebuilt import ToolNode
    from langgraph.checkpoint.sqlite import SqliteSaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False

from agent.schemas import ReviewFinding, ReviewReport, ReviewVerdict, Severity
from agent.tools.git_diff_reader import GitDiffReader
from agent.tools.file_context_reader import FileContextReader, create_file_context_tools
from agent.harness.step_logger import StepLogger
from agent.harness.validator import FindingValidator


# ─────────────────────────────────────────────────────────────
# Agent State (TypedDict cho LangGraph compatibility)
# ─────────────────────────────────────────────────────────────

class ReviewState(TypedDict, total=False):
    """State của LangGraph workflow — được serialize vào SQLite checkpoint."""
    # Input
    pr_number: int
    repo_full_name: str
    commit_sha: str
    diff_text: str
    repo_root: str
    
    # Parsed diff
    parsed_files: dict         # Output từ GitDiffReader
    changed_file_paths: list[str]
    
    # Agent execution
    messages: list             # LangChain messages (cho LLM)
    tool_calls_count: int
    
    # Findings accumulation  
    raw_findings: list[dict]   # Findings thô từ LLM (chưa validate)
    validated_findings: list[dict]  # Findings đã pass validator
    invalid_findings: list[dict]    # Findings bị reject
    
    # Verdict
    verdict: str
    review_summary: str
    
    # Tracking
    current_node: str
    step_count: int
    error_log: list[str]
    run_id: str
    
    # Phase 1: UC-01 specific
    hunks_processed: list[str]  # Track hunk đã xử lý
    guard_passed: bool


# ─────────────────────────────────────────────────────────────
# Prompts
# ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Bạn là một Code Review Agent chuyên nghiệp cho nhóm phát triển phần mềm.

NHIỆM VỤ: Phân tích git diff của Pull Request và sinh danh sách findings có cấu trúc.

QUY TẮC BẮT BUỘC:
1. CHỈ comment vào các dòng THỰC SỰ CÓ trong diff (dòng mới thêm vào, có dấu '+')
2. KHÔNG đoán hoặc bịa số dòng — kiểm tra kỹ số dòng ở phiên bản HEAD trong hunk
3. Mỗi finding PHẢI có: file, line, severity, category, message, suggestion (nếu có), confidence
4. KHÔNG comment vào dòng không thay đổi (nợ cũ), trừ khi nó trực tiếp gây ra lỗi ở dòng mới
5. Severity: critical (security/crash) > major (logic/perf) > minor (missing edge case) > nit (style)
6. Kết thúc bằng structured verdict: approve (nếu sạch) / request_changes (nếu có lỗi critical/major) / comment (nếu chỉ có nit/minor)

BẮT BUỘC ĐỊNH DẠNG ĐẦU RA:
Bạn PHẢI trả về câu trả lời có chứa một khối JSON chuẩn trong cặp ```json ... ``` như sau:
```json
{{
  "summary": "Tóm tắt ngắn gọn kết quả review",
  "verdict": "request_changes",
  "findings": [
    {{
      "file": "app/services/booking.py",
      "line": 43,
      "severity": "critical",
      "category": "logic",
      "message": "Giải thích rõ ràng: vấn đề là gì, tại sao sai (tối thiểu 10 ký tự)",
      "suggestion": "    return table.max_capacity >= requested",
      "confidence": 0.95
    }}
  ]
}}
```

GIỚI HẠN:
- Tối đa {max_tool_calls} lần gọi tool mỗi PR
- Tối đa {max_findings} findings mỗi PR
- Chỉ review file trong diff, không lan sang file khác không liên quan

BỐI CẢNH DỰ ÁN:
- Repo: Hệ thống đặt bàn "Cà phê Sông Hàn" (Python)
- Ngôn ngữ: Python
- Framework: FastAPI / SQLAlchemy
"""

REVIEW_INSTRUCTION = """Hãy review PR sau:

PR #{pr_number}
Repo: {repo}
Commit: {commit_sha}

DIFF:
```
{diff_text}
```

Hướng dẫn:
1. Đọc kỹ git diff (chú ý hunk header @@ -a,b +c,d @@ và đếm đúng số dòng mới thêm vào)
2. Phân tích lỗi logic, bảo mật, convention
3. Trả về đúng định dạng JSON có chứa danh sách findings và verdict

Bắt đầu phân tích:"""


def _extract_findings_from_response(content: str) -> tuple[list[dict], str, str]:
    """
    Trích xuất findings, verdict, summary từ văn bản phản hồi của LLM.
    Trả về: (findings_list, verdict, summary)
    """
    import json
    import re

    findings: list[dict] = []
    verdict = "comment"
    summary = ""

    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    data = None
    if match:
        try:
            data = json.loads(match.group(1))
        except Exception:
            pass

    if data is None:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                data = json.loads(content[start:end + 1])
            except Exception:
                pass

    if isinstance(data, dict):
        summary = str(data.get("summary", ""))
        verdict = str(data.get("verdict", "comment")).lower()
        raw_list = data.get("findings", [])
        if isinstance(raw_list, list):
            for item in raw_list:
                if not isinstance(item, dict):
                    continue
                file_path = str(item.get("file", "")).strip()
                try:
                    line_num = int(item.get("line", 0))
                except (ValueError, TypeError):
                    line_num = 0
                msg = str(item.get("message", "")).strip()
                if not file_path or line_num < 1 or len(msg) < 5:
                    continue

                sev = str(item.get("severity", "major")).lower()
                if sev not in ("critical", "major", "minor", "nit"):
                    sev = "major"

                cat = str(item.get("category", "logic")).lower()
                if cat not in ("logic", "security", "performance", "convention", "test", "other"):
                    cat = "logic"

                conf = item.get("confidence", 0.9)
                try:
                    conf = float(conf)
                    conf = max(0.0, min(1.0, conf))
                except (ValueError, TypeError):
                    conf = 0.9

                finding_dict = {
                    "file": file_path,
                    "line": line_num,
                    "side": "RIGHT",
                    "severity": sev,
                    "category": cat,
                    "message": msg,
                    "suggestion": item.get("suggestion"),
                    "confidence": conf,
                    "rule_ref": item.get("rule_ref"),
                    "tool_source": item.get("tool_source"),
                }
                findings.append(finding_dict)

    return findings, verdict, summary


# ─────────────────────────────────────────────────────────────
# Node Functions
# ─────────────────────────────────────────────────────────────

def node_fetch_and_parse(state: ReviewState) -> dict:
    """
    Node 1: Parse git diff thành structured data.
    Lớp harness: Tools + Context
    """
    diff_text = state.get("diff_text", "")
    
    if not diff_text.strip():
        return {
            "error_log": ["Diff rỗng — không có gì để review"],
            "guard_passed": False,
            "current_node": "fetch_parse",
        }
    
    # Giới hạn kích thước diff (UC-05 sẽ xử lý PR lớn)
    max_diff_lines = int(os.getenv("MAX_DIFF_LINES", "3000"))
    diff_lines = diff_text.splitlines()
    
    if len(diff_lines) > max_diff_lines:
        # Truncate và ghi cảnh báo
        diff_text = "\n".join(diff_lines[:max_diff_lines])
        warning = f"⚠️ Diff bị cắt: {len(diff_lines)} dòng → {max_diff_lines} dòng (UC-05 sẽ xử lý PR lớn)"
        error_log = state.get("error_log", []) + [warning]
    else:
        error_log = state.get("error_log", [])
    
    # Parse diff
    reader = GitDiffReader()
    parsed = reader.parse(diff_text)
    summary = reader.get_summary(parsed)
    
    return {
        "parsed_files": {
            f.path: {
                "added_lines": f.added_lines,
                "removed_lines": f.removed_lines,
                "all_valid_lines": list(f.all_valid_lines),
                "is_new_file": f.is_new_file,
                "is_deleted_file": f.is_deleted_file,
            }
            for f in parsed.files
        },
        "changed_file_paths": parsed.changed_file_paths,
        "diff_text": diff_text,  # Updated (possibly truncated)
        "error_log": error_log,
        "current_node": "fetch_parse",
        "guard_passed": True,
        "hunks_processed": [],
    }


def node_guard(state: ReviewState) -> dict:
    """
    Node 2: Guard harness — kiểm tra an toàn trước khi review.
    Lớp harness: Guardrails + Security
    
    Phát hiện:
    - Diff quá lớn (DoS)
    - Tên file nguy hiểm (prompt injection)
    - PR rỗng
    """
    if not state.get("guard_passed", False):
        return {"current_node": "guard", "guard_passed": False}
    
    changed_files = state.get("changed_file_paths", [])
    errors = state.get("error_log", [])
    
    # Phát hiện tên file injection (UC Security Case 2)
    suspicious_names = [
        "ignore_previous_instructions",
        "SYSTEM:",
        "approve_all",
    ]
    for f in changed_files:
        if any(s.lower() in f.lower() for s in suspicious_names):
            errors.append(
                f"🛡️ Guard: Phát hiện tên file nghi ngờ injection: {f}. "
                f"Tiếp tục review bình thường, bỏ qua tên file."
            )
    
    # Kiểm tra có file nào để review không
    if not changed_files:
        errors.append("Guard: Không có file nào để review")
        return {
            "guard_passed": False, 
            "error_log": errors,
            "current_node": "guard"
        }
    
    return {
        "guard_passed": True,
        "error_log": errors,
        "current_node": "guard",
    }


def node_review(state: ReviewState, llm, tools: list) -> dict:
    """
    Node 3: Core Review — LLM phân tích diff với ReAct pattern.
    Lớp harness: Model + Context + Tools + Skills
    """
    if not state.get("guard_passed", False):
        return {"current_node": "review", "verdict": "comment"}
    
    pr_number = state.get("pr_number", 0)
    commit_sha = state.get("commit_sha", "unknown")[:8]
    repo = state.get("repo_full_name", "unknown/repo")
    diff_text = state.get("diff_text", "")
    max_tool_calls = int(os.getenv("MAX_TOOL_CALLS_PER_PR", "30"))
    max_findings = int(os.getenv("MAX_FINDINGS_PER_PR", "15"))
    
    # Build messages
    system_msg = SystemMessage(content=SYSTEM_PROMPT.format(
        max_tool_calls=max_tool_calls,
        max_findings=max_findings,
    ))
    
    human_msg = HumanMessage(content=REVIEW_INSTRUCTION.format(
        pr_number=pr_number,
        repo=repo,
        commit_sha=commit_sha,
        diff_text=diff_text[:8000],  # Giới hạn trong context
    ))
    
    messages = [system_msg, human_msg]
    
    # LLM với tools binding (nếu có tools)
    if tools:
        llm_with_tools = llm.bind_tools(tools)
    else:
        llm_with_tools = llm
    
    raw_findings = state.get("raw_findings", [])
    tool_calls_count = state.get("tool_calls_count", 0)
    verdict = state.get("verdict", "comment")
    summary = state.get("review_summary", "")
    tool_map = {t.name: t for t in tools} if tools else {}
    max_iterations = 5

    try:
        for _ in range(max_iterations):
            response = llm_with_tools.invoke(messages)
            messages.append(response)
            
            tool_calls = getattr(response, "tool_calls", None)
            if tool_calls and tool_calls_count < max_tool_calls:
                for tc in tool_calls:
                    t_name = tc.get("name")
                    t_args = tc.get("args", {})
                    t_id = tc.get("id", f"call_{tool_calls_count}")
                    
                    target_tool = tool_map.get(t_name)
                    if target_tool:
                        try:
                            t_res = target_tool.invoke(t_args)
                        except Exception as te:
                            t_res = f"Tool execution error: {te}"
                    else:
                        t_res = f"Tool '{t_name}' not available"
                        
                    tool_msg = ToolMessage(content=str(t_res), tool_call_id=t_id, name=t_name)
                    messages.append(tool_msg)
                    tool_calls_count += 1
                # Tiếp tục vòng lặp để LLM nhận quan sát từ tools
                continue
            
            # Không có tool_calls nữa -> trích xuất kết quả review cuối cùng
            resp_content = response.content if hasattr(response, "content") else str(response)
            extracted_findings, parsed_verdict, parsed_summary = _extract_findings_from_response(resp_content)
            
            if extracted_findings:
                raw_findings.extend(extracted_findings)
            if parsed_verdict:
                verdict = parsed_verdict
            if parsed_summary:
                summary = parsed_summary
            break
            
    except Exception as e:
        error_log = state.get("error_log", []) + [f"LLM error: {e}"]
        return {
            "current_node": "review",
            "error_log": error_log,
            "verdict": "comment",
        }
    
    return {
        "messages": messages,
        "raw_findings": raw_findings,
        "tool_calls_count": tool_calls_count,
        "verdict": verdict,
        "review_summary": summary,
        "current_node": "review",
    }


def node_validate(state: ReviewState) -> dict:
    """
    Node 4: Validate findings trước khi publish.
    Lớp harness: Verification + Guardrails
    """
    raw_findings_data = state.get("raw_findings", [])
    diff_text = state.get("diff_text", "")
    
    # Rebuild ParsedDiff để validate
    reader = GitDiffReader()
    parsed = reader.parse(diff_text) if diff_text else None
    
    # Convert dict → ReviewFinding
    raw_findings = []
    for f in raw_findings_data:
        try:
            if isinstance(f, dict):
                finding = ReviewFinding(**f)
            else:
                finding = f
            raw_findings.append(finding)
        except Exception as e:
            error_log = state.get("error_log", [])
            error_log.append(f"Schema validation error: {e}")
    
    # Run validator
    validator = FindingValidator(parsed_diff=parsed)
    result = validator.validate_batch(raw_findings)
    
    error_log = state.get("error_log", [])
    if result.invalid:
        for f, errors in result.invalid:
            error_log.append(f"Invalid finding {f.file}:{f.line} — {'; '.join(errors)}")
    
    # Determine verdict
    has_critical = any(
        f.severity == Severity.CRITICAL for f in result.valid
    )
    has_major = any(
        f.severity == Severity.MAJOR for f in result.valid
    )
    
    if has_critical or has_major:
        verdict = ReviewVerdict.REQUEST_CHANGES.value
    elif result.valid:
        verdict = ReviewVerdict.COMMENT.value
    else:
        verdict = ReviewVerdict.APPROVE.value
    
    return {
        "validated_findings": [f.model_dump() for f in result.valid],
        "invalid_findings": [
            {"finding": f.model_dump(), "errors": errs} 
            for f, errs in result.invalid
        ],
        "verdict": verdict,
        "error_log": error_log,
        "current_node": "validate",
    }


# ─────────────────────────────────────────────────────────────
# Graph Builder
# ─────────────────────────────────────────────────────────────

def build_review_graph(repo_root: str = ".", checkpoint_db: str = "./checkpoints/agent.db"):
    """
    Xây dựng LangGraph StateGraph cho Code Review Agent.
    
    Args:
        repo_root: Đường dẫn đến repo được review
        checkpoint_db: Đường dẫn SQLite cho checkpoint (resume capability)
    
    Returns:
        Compiled LangGraph app
    """
    if not LANGGRAPH_AVAILABLE:
        raise ImportError("Cần cài langgraph: pip install langgraph")
    
    # Setup LLM
    model_name = os.getenv("LLM_MODEL", "gpt-4o-mini")
    if ChatOpenAI is None:
        raise ImportError("Cần cài langchain-openai: pip install langchain-openai")
    
    base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE")
    api_key = os.getenv("OPENAI_API_KEY", "not-needed")
    
    llm_kwargs = {
        "model": model_name,
        "temperature": 0.0,  # Deterministic output
        "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "4096")),
        "api_key": api_key,
    }
    if base_url:
        llm_kwargs["base_url"] = base_url
        
    llm = ChatOpenAI(**llm_kwargs)
    
    # Setup tools
    tools = create_file_context_tools(repo_root=repo_root)
    
    # Build graph
    workflow = StateGraph(ReviewState)
    
    # Add nodes
    workflow.add_node("fetch_parse", node_fetch_and_parse)
    workflow.add_node("guard", node_guard)
    workflow.add_node("review", lambda state: node_review(state, llm, tools))
    workflow.add_node("validate", node_validate)
    
    if tools:
        workflow.add_node("tools", ToolNode(tools))
    
    # Add edges (flow)
    workflow.add_edge(START, "fetch_parse")
    workflow.add_edge("fetch_parse", "guard")
    
    # Conditional edge: guard passed → review, else END
    workflow.add_conditional_edges(
        "guard",
        lambda state: "review" if state.get("guard_passed", False) else END,
        {"review": "review", END: END}
    )
    
    workflow.add_edge("review", "validate")
    workflow.add_edge("validate", END)
    
    # Setup SQLite checkpointer
    import os as _os
    _os.makedirs(_os.path.dirname(checkpoint_db) if _os.path.dirname(checkpoint_db) else ".", exist_ok=True)
    
    try:
        checkpointer = SqliteSaver.from_conn_string(checkpoint_db)
        compiled = workflow.compile(checkpointer=checkpointer)
    except Exception:
        # Fallback: compile without checkpointer
        compiled = workflow.compile()
    
    return compiled


# ─────────────────────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────────────────────

def run_review(
    pr_number: int,
    diff_text: str,
    repo: str = "unknown/repo",
    commit_sha: str = "HEAD",
    repo_root: str = ".",
    verbose: bool = True,
) -> dict:
    """
    Chạy review cho một PR.
    
    Args:
        pr_number: Số PR
        diff_text: Raw git diff text
        repo: "owner/repo"
        commit_sha: SHA của commit
        repo_root: Đường dẫn local repo
        verbose: In log ra console
    
    Returns:
        ReviewReport dict
    """
    # Setup logger
    logger = StepLogger(
        pr_number=pr_number,
        commit_sha=commit_sha,
        repo=repo,
        log_dir="./logs",
        console_output=verbose,
    )
    
    logger.log_step(
        thought=f"Bắt đầu review PR #{pr_number} @ {commit_sha[:8]}",
        is_final=False,
    )
    
    # Initial state
    initial_state: ReviewState = {
        "pr_number": pr_number,
        "repo_full_name": repo,
        "commit_sha": commit_sha,
        "diff_text": diff_text,
        "repo_root": repo_root,
        "messages": [],
        "tool_calls_count": 0,
        "raw_findings": [],
        "validated_findings": [],
        "invalid_findings": [],
        "verdict": "comment",
        "review_summary": "",
        "current_node": "init",
        "step_count": 0,
        "error_log": [],
        "run_id": logger.run_id,
        "hunks_processed": [],
        "guard_passed": False,
        "changed_file_paths": [],
        "parsed_files": {},
    }
    
    try:
        graph = build_review_graph(repo_root=repo_root)
        config = {"configurable": {"thread_id": logger.run_id}}
        
        start = time.monotonic()
        final_state = graph.invoke(initial_state, config=config)
        latency_ms = (time.monotonic() - start) * 1000
        
        validated = final_state.get("validated_findings", [])
        verdict = final_state.get("verdict", "comment")
        
        logger.log_step(
            thought="Review hoàn thành, validate findings",
            observation=f"Verdict: {verdict} | Findings: {len(validated)}",
            latency_ms=latency_ms,
            is_final=True,
        )
        
        summary = logger.finalize(verdict=verdict, findings=validated)
        
        return {
            "run_id": logger.run_id,
            "pr_number": pr_number,
            "commit_sha": commit_sha,
            "verdict": verdict,
            "findings": validated,
            "error_log": final_state.get("error_log", []),
            "trace_path": logger.trace_path,
            "stats": {
                "total_steps": summary.total_steps,
                "total_tool_calls": summary.total_tool_calls,
                "total_tokens": summary.total_tokens,
                "total_cost_usd": summary.total_cost_usd,
                "latency_ms": latency_ms,
            }
        }
    
    except Exception as e:
        logger.log_step(error=str(e), is_final=True)
        logger.finalize(verdict="comment")
        return {
            "run_id": logger.run_id,
            "error": str(e),
            "verdict": "comment",
            "findings": [],
        }
