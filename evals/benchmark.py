"""
evals/benchmark.py — Bộ Đánh Giá Chất Lượng Agent Tự Động (SE373)
===================================================================
- Tiêu chí 3: Recall >= 50%, Precision >= 50%, Độ chính xác vị trí dòng (±3 dòng) >= 80%.
- Tiêu chí 5: Trên PR sạch, trung bình <= 2 finding mức major trở lên mỗi PR.

Hỗ trợ chạy cả chế độ LIVE (gọi 9Router thật) lẫn MOCK (chạy kiểm thử nhanh).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Đảm bảo in tiếng Việt trên console Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Thêm thư mục gốc vào sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from unittest.mock import MagicMock

from langchain_core.messages import AIMessage
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from agent import Severity, StepLogger, run_code_review

console = Console()
GROUND_TRUTH_FILE = PROJECT_ROOT / "evals" / "dataset" / "ground_truth.json"


def get_mock_response_for_case(case_id: str) -> str:
    """Trả về phản hồi chuẩn xác giả lập cho từng ca kiểm thử khi chạy chế độ mock."""
    if case_id == "01_single_line_logic":
        return json.dumps({
            "summary": "Phát hiện lỗi logic nghiêm trọng ở hàm check_capacity làm đảo ngược điều kiện >= thành <=.",
            "findings": [{
                "file": "app/services/booking.py",
                "line": 43,
                "side": "RIGHT",
                "severity": "major",
                "category": "logic",
                "message": "Toán tử so sánh bị đảo ngược từ >= thành <= dẫn đến việc nhận quá tải khách.",
                "suggestion": "    return table.max_capacity >= requested",
                "confidence": 0.98,
            }]
        })
    elif case_id == "02_clean_pr":
        return json.dumps({
            "summary": "PR sạch sẽ, bổ sung docstring và hàm tiện ích format tiền tệ đúng chuẩn.",
            "findings": []
        })
    elif case_id == "03_delete_only":
        return json.dumps({
            "summary": "PR chỉ xóa bỏ mã nguồn cũ không còn sử dụng, không có mã mới nào thêm vào.",
            "findings": []
        })
    elif case_id == "04_rename_file":
        return json.dumps({
            "summary": "Đổi tên file và thêm điều kiện bảo vệ balance >= 0 hợp lệ.",
            "findings": []
        })
    elif case_id == "05_multi_file_call":
        return json.dumps({
            "summary": "Phát hiện lỗi gọi hàm process_payment bị đảo ngược thứ tự tham số.",
            "findings": [{
                "file": "app/controllers/order_controller.py",
                "line": 27,
                "side": "RIGHT",
                "severity": "major",
                "category": "logic",
                "message": "Hàm process_payment yêu cầu (user_id, amount) nhưng đang truyền (amount, user_id).",
                "suggestion": "    return process_payment(user_id=user_id, amount=total_amount)",
                "confidence": 0.95,
            }]
        })
    elif case_id == "06_sql_injection":
        return json.dumps({
            "summary": "Phát hiện lỗ hổng bảo mật nghiêm trọng: SQL Injection qua chuỗi f-string.",
            "findings": [{
                "file": "app/repositories/user_repo.py",
                "line": 14,
                "side": "RIGHT",
                "severity": "critical",
                "category": "security",
                "message": "Nối chuỗi f-string trực tiếp vào câu lệnh SQL gây nguy cơ SQL Injection nghiêm trọng.",
                "suggestion": '    query = "SELECT * FROM users WHERE email = :email"\n    return db.execute(query, {"email": email}).fetchone()',
                "confidence": 0.99,
            }]
        })
    elif case_id == "07_hardcoded_secret":
        return json.dumps({
            "summary": "Phát hiện lộ thông tin nhạy cảm: API Key Stripe được gán cứng trong mã nguồn.",
            "findings": [{
                "file": "app/config/payment.py",
                "line": 6,
                "side": "RIGHT",
                "severity": "critical",
                "category": "security",
                "message": "Tuyệt đối không lưu API key hoặc secret trực tiếp trong mã nguồn; hãy dùng biến môi trường.",
                "suggestion": '    API_KEY = os.getenv("STRIPE_SECRET_KEY", "")',
                "confidence": 0.99,
            }]
        })
    elif case_id == "08_zero_division":
        return json.dumps({
            "summary": "Phát hiện lỗi logic: Nguy cơ văng ZeroDivisionError khi danh sách điểm rỗng.",
            "findings": [{
                "file": "app/analytics/metrics.py",
                "line": 20,
                "side": "RIGHT",
                "severity": "major",
                "category": "logic",
                "message": "Biểu thức len(scores) sẽ bằng 0 khi scores rỗng dẫn đến ZeroDivisionError.",
                "suggestion": "    return sum(scores) / len(scores) if scores else 0.0",
                "confidence": 0.95,
            }]
        })
    elif case_id == "09_infinite_loop":
        return json.dumps({
            "summary": "Phát hiện nguy cơ treo hệ thống: Vòng lặp while True thiếu điều kiện thoát.",
            "findings": [{
                "file": "app/sync/job_poller.py",
                "line": 34,
                "side": "RIGHT",
                "severity": "major",
                "category": "logic",
                "message": "Vòng lặp while True không kiểm tra khi queue rỗng (job is None) dẫn đến vòng lặp vô tận.",
                "suggestion": "        if not job:\n            break\n        process_job(job)",
                "confidence": 0.96,
            }]
        })
    elif case_id == "10_n_plus_one_query":
        return json.dumps({
            "summary": "Phát hiện vấn đề hiệu năng nghiêm trọng: Truy vấn N+1 database bên trong vòng lặp.",
            "findings": [{
                "file": "app/services/invoice_service.py",
                "line": 26,
                "side": "RIGHT",
                "severity": "major",
                "category": "performance",
                "message": "Truy vấn database trong từng vòng lặp for gây ra N+1 query bottleneck; nên dùng IN clause.",
                "suggestion": "    return db.session.query(Invoice).filter(Invoice.user_id.in_(user_ids)).all()",
                "confidence": 0.94,
            }]
        })
    return json.dumps({"summary": "Mặc định", "findings": []})



def run_benchmark(mock: bool = False):
    """Thực thi benchmark trên toàn bộ bộ dữ liệu evals."""
    banner = Text()
    banner.append("📊 BENCHMARK ĐÁNH GIÁ CHẤT LƯỢNG AGENT · SE373\n", style="bold cyan")
    banner.append("Kiểm định Tiêu chí 3 (Precision/Recall >= 50%) và Tiêu chí 5 (PR sạch <= 2 major)", style="italic white")
    console.print(Panel(banner, border_style="cyan"))

    if not GROUND_TRUTH_FILE.exists():
        console.print(f"[bold red]Lỗi:[/bold red] Không tìm thấy file {GROUND_TRUTH_FILE}")
        sys.exit(1)

    ground_truth = json.loads(GROUND_TRUTH_FILE.read_text(encoding="utf-8"))
    console.print(f"📁 Tải thành công {len(ground_truth)} ca kiểm thử từ dataset.\n")

    results_table = Table(title="Kết Quả Chi Tiết Từng Kịch Bản", header_style="bold magenta", expand=True)
    results_table.add_column("Ca Test", style="cyan", width=22)
    results_table.add_column("Loại PR", width=22)
    results_table.add_column("Kỳ Vọng", justify="center", width=14)
    results_table.add_column("Thực Tế", justify="center", width=14)
    results_table.add_column("TP", justify="center", style="green", width=5)
    results_table.add_column("FP", justify="center", style="red", width=5)
    results_table.add_column("FN", justify="center", style="yellow", width=5)
    results_table.add_column("Precision", justify="right", width=10)
    results_table.add_column("Recall", justify="right", width=10)

    total_tp = 0
    total_fp = 0
    total_fn = 0
    line_accurate_count = 0
    clean_pr_major_findings = []

    for case_id, case_info in ground_truth.items():
        diff_path = PROJECT_ROOT / case_info["diff_file"]
        if not diff_path.exists():
            console.print(f"[red]Bỏ qua {case_id}: Không thấy file diff {diff_path}[/red]")
            continue

        diff_text = diff_path.read_text(encoding="utf-8")

        # Chọn mock hoặc live LLM
        custom_llm = None
        if mock:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = AIMessage(content=f"```json\n{get_mock_response_for_case(case_id)}\n```")
            mock_llm.model_name = "mock-eval-llm"
            custom_llm = mock_llm

        logger = StepLogger(run_id=f"bench_{case_id}")

        with console.status(f"[bold green]Đang đánh giá ca: {case_info['name']}...[/bold green]"):
            report = run_code_review(
                diff_text=diff_text,
                pr_number=99,
                custom_llm=custom_llm,
                logger=logger,
            )

        expected_findings = case_info.get("expected_findings", [])
        is_clean = case_info.get("is_clean", False)
        actual_findings = report.findings

        tp = 0
        fp = 0
        fn = 0

        if is_clean:
            # Đối với PR sạch
            major_count = sum(1 for f in actual_findings if f.severity in (Severity.MAJOR, Severity.CRITICAL))
            clean_pr_major_findings.append(major_count)
            fp = len(actual_findings)
        else:
            # Đối với PR có lỗi cần bắt
            matched_expected = set()
            for af in actual_findings:
                matched = False
                for idx, ef in enumerate(expected_findings):
                    if idx in matched_expected:
                        continue
                    # So khớp file và dòng (trong khoảng ±3 dòng)
                    file_match = (af.file.lower() == ef["file"].lower())
                    line_range = ef.get("line_range", [ef["line"] - 3, ef["line"] + 3])
                    line_match = (line_range[0] <= af.line <= line_range[1])

                    if file_match and line_match:
                        matched = True
                        matched_expected.add(idx)
                        tp += 1
                        if abs(af.line - ef["line"]) <= 3:
                            line_accurate_count += 1
                        break

                if not matched:
                    fp += 1

            fn = len(expected_findings) - len(matched_expected)

        total_tp += tp
        total_fp += fp
        total_fn += fn

        # Tính chỉ số cho từng ca
        prec = (tp / (tp + fp)) * 100 if (tp + fp) > 0 else (100.0 if is_clean and fp == 0 else 0.0)
        rec = (tp / (tp + fn)) * 100 if (tp + fn) > 0 else (100.0 if is_clean else 0.0)

        exp_verdict_str = case_info["expected_verdict"].upper()
        act_verdict_str = report.verdict.value.upper()

        results_table.add_row(
            case_id,
            case_info["name"][:22],
            exp_verdict_str,
            act_verdict_str,
            str(tp),
            str(fp),
            str(fn),
            f"{prec:.1f}%",
            f"{rec:.1f}%",
        )

    console.print(results_table)

    overall_precision = (total_tp / (total_tp + total_fp) * 100) if (total_tp + total_fp) > 0 else 100.0
    overall_recall = (total_tp / (total_tp + total_fn) * 100) if (total_tp + total_fn) > 0 else 100.0
    line_accuracy = (line_accurate_count / total_tp * 100) if total_tp > 0 else 100.0
    avg_clean_major = sum(clean_pr_major_findings) / len(clean_pr_major_findings) if clean_pr_major_findings else 0.0

    console.print("\n" + "=" * 70)
    console.print("🎯 [bold]ĐỐI CHIẾU TIÊU CHÍ CHẤP NHẬN CỦA THẦY QUÍ[/bold]")
    console.print("=" * 70)

    # 1. Precision Check (>= 50%)
    p_pass = overall_precision >= 50.0
    p_status = "[bold green]✅ ĐẠT CHUẨN[/bold green]" if p_pass else "[bold red]❌ CHƯA ĐẠT[/bold red]"
    console.print(f"• [bold]Precision (Độ chính xác):[/bold] {overall_precision:.1f}%  (Mục tiêu: >= 50.0%) ➔ {p_status}")

    # 2. Recall Check (>= 50%)
    r_pass = overall_recall >= 50.0
    r_status = "[bold green]✅ ĐẠT CHUẨN[/bold green]" if r_pass else "[bold red]❌ CHƯA ĐẠT[/bold red]"
    console.print(f"• [bold]Recall (Độ bao phủ):[/bold] {overall_recall:.1f}%  (Mục tiêu: >= 50.0%) ➔ {r_status}")

    # 3. Line Accuracy Check (>= 80%)
    l_pass = line_accuracy >= 80.0
    l_status = "[bold green]✅ ĐẠT CHUẨN[/bold green]" if l_pass else "[bold red]❌ CHƯA ĐẠT[/bold red]"
    console.print(f"• [bold]Độ chính xác vị trí dòng (±3 dòng):[/bold] {line_accuracy:.1f}%  (Mục tiêu: >= 80.0%) ➔ {l_status}")

    # 4. Clean PR Major Findings Check (<= 2)
    c_pass = avg_clean_major <= 2.0
    c_status = "[bold green]✅ ĐẠT CHUẨN[/bold green]" if c_pass else "[bold red]❌ CHƯA ĐẠT[/bold red]"
    console.print(f"• [bold]Lỗi Major trên PR sạch:[/bold] trung bình {avg_clean_major:.1f} lỗi/PR  (Mục tiêu: <= 2.0) ➔ {c_status}")

    all_passed = p_pass and r_pass and l_pass and c_pass
    if all_passed:
        console.print(Panel("[bold white on green] 🎉 CHÚC MỪNG: TOÀN BỘ CÁC TIÊU CHÍ ĐÁNH GIÁ ĐÃ ĐẠT CHUẨN XUẤT SẮC! [/bold white on green]"))
    else:
        console.print(Panel("[bold white on yellow] ⚠️ CẦN TINH CHỈNH THÊM ĐỂ ĐẠT 100% CÁC TIÊU CHÍ [/bold white on yellow]"))

    return all_passed


if __name__ == "__main__":
    is_mock = "--mock" in sys.argv
    run_benchmark(mock=is_mock)
