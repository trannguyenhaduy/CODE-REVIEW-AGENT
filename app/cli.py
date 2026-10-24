"""
app/cli.py — Giao diện Dòng Lệnh Chuyên Nghiệp (Rich CLI Interface)
=====================================================================
Đáp ứng tiêu chuẩn Đồ án SE373 (Mảng 2.5 điểm Phần mềm):
- Hiển thị Banner thương hiệu môn học và đề tài.
- Trình diễn phán quyết PR rõ ràng (APPROVE, COMMENT, REQUEST_CHANGES).
- Bảng hiển thị danh sách lỗi chi tiết kèm gợi ý sửa code 1-click chuẩn GitHub.
- Bảng kiểm toán thời gian thực thi (Latency) và Token usage từ StepLogger.
- Hỗ trợ cờ --mock cho chế độ chạy offline / demo khi chưa bật proxy.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Đảm bảo in tiếng Việt trên console Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Đảm bảo Python nhận diện thư mục gốc của project
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from unittest.mock import MagicMock

import click
from langchain_core.messages import AIMessage
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from agent import ReviewVerdict, Severity, StepLogger, run_code_review

console = Console()


def render_banner():
    """In banner tiêu đề thương hiệu của Agent."""
    banner_text = Text()
    banner_text.append("🤖 CODE REVIEW AGENT · SE373 (UIT)\n", style="bold cyan")
    banner_text.append("Autonomous Pull Request Reviewer with LangGraph & Verification Harness\n", style="italic white")
    banner_text.append("Khoa Công nghệ Phần mềm — ĐH Công nghệ Thông tin (ĐHQG-HCM)", style="dim")

    console.print(Panel(banner_text, border_style="cyan", padding=(1, 2)))


def get_mock_llm():
    """Tạo Mock LLM cho chế độ demo / offline."""
    mock_content = """```json
{
  "summary": "Phát hiện lỗi logic nghiêm trọng ở hàm check_capacity làm đảo ngược điều kiện so sánh. Cần sửa trước khi merge.",
  "findings": [
    {
      "file": "app/services/booking.py",
      "line": 43,
      "side": "RIGHT",
      "severity": "major",
      "category": "logic",
      "message": "Toán tử so sánh bị đảo ngược từ >= thành <= dẫn đến việc bàn quá tải khách so với sức chứa.",
      "suggestion": "    return table.max_capacity >= requested",
      "confidence": 0.98
    }
  ]
}
```"""
    mock = MagicMock()
    mock.invoke.return_value = AIMessage(content=mock_content)
    mock.model_name = "mock-gemini-flash"
    return mock


@click.group()
def cli():
    """Hệ thống Đánh giá Mã Nguồn Tự Động (Code Review Agent)."""
    pass


@cli.command()
@click.option("--diff", "-d", type=click.Path(exists=True), default=None, help="Đường dẫn file Git Diff (.diff hoặc .patch)")
@click.option("--url", "-u", default=None, help="Đường dẫn GitHub Pull Request (vd: https://github.com/owner/repo/pull/1)")
@click.option("--pr", "-p", default=None, type=int, help="Số hiệu Pull Request (mặc định: tự trích xuất từ URL hoặc 42)")
@click.option("--repo", "-r", default=None, help="Tên repository (mặc định: tự trích xuất từ URL hoặc uit/cafe-song-han)")
@click.option("--commit", "-c", default="HEAD", help="Mã commit SHA (mặc định: HEAD)")
@click.option("--mock", "-m", is_flag=True, default=False, help="Chạy chế độ giả lập offline để demo nhanh không cần mở 9Router")
@click.option("--out", "-o", type=click.Path(), default=None, help="Đường dẫn file JSON xuất kết quả báo cáo")
def review(diff: str | None, url: str | None, pr: int | None, repo: str | None, commit: str, mock: bool, out: str | None):
    """Tiến hành rà soát tự động một file Git Diff hoặc một GitHub Pull Request."""
    render_banner()

    if not diff and not url:
        console.print("[bold red]❌ Lỗi:[/bold red] Vui lòng cung cấp file diff (`--diff`) hoặc đường dẫn GitHub PR (`--url`)!")
        console.print("[dim yellow]Ví dụ: python app/cli.py review --url https://github.com/trannguyenhaduy/se373-demo-target/pull/1[/dim yellow]")
        return

    diff_text = ""
    if url:
        from app.server import fetch_github_diff
        console.print(f"[bold cyan]🔗 Đang kết nối GitHub và kéo Git Diff từ:[/bold cyan] [white]{url}[/white]")
        try:
            diff_text, fetched_repo, fetched_pr = fetch_github_diff(url)
            repo = repo or fetched_repo
            pr = pr or fetched_pr
            console.print(f"[bold green]✅ Tải thành công:[/bold green] PR #{pr} ({len(diff_text.splitlines())} dòng diff)")
        except Exception as e:
            console.print(f"[bold red]❌ Không thể tải diff từ GitHub:[/bold red] {e}")
            return
    else:
        diff_path = Path(diff)
        diff_text = diff_path.read_text(encoding="utf-8")
        console.print(f"[bold yellow]📂 Đang tải Git Diff:[/bold yellow] [white]{diff_path.resolve()}[/white]")
        pr = pr or 42
        repo = repo or "uit/cafe-song-han"

    console.print(f"[bold yellow]📌 Thông tin PR:[/bold yellow] #{pr} | Repo: [cyan]{repo}[/cyan] | Commit: [magenta]{commit}[/magenta]")
    if mock:
        console.print("[bold magenta]🧪 Chế độ: MOCK OFFLINE (Giả lập phản hồi LLM)[/bold magenta]\n")
    else:
        console.print("[bold green]🌐 Chế độ: LIVE LLM (Kết nối endpoint trong .env)[/bold green]\n")

    logger = StepLogger(log_dir="logs")
    custom_llm = get_mock_llm() if mock else None

    # Hiệu ứng Spinner chạy qua các trạm của LangGraph
    with console.status("[bold green]Agent đang phân tích mã nguồn qua 4 trạm LangGraph...[/bold green]", spinner="dots"):
        try:
            report = run_code_review(
                diff_text=diff_text,
                pr_number=pr,
                commit_sha=commit,
                repo=repo,
                custom_llm=custom_llm,
                logger=logger,
            )
        except Exception as e:
            console.print(f"\n[bold red]❌ Lỗi khi thực thi Review Agent:[/bold red] {e}")
            if not mock:
                console.print("[dim yellow]💡 Mẹo: Nếu 9Router chưa bật, bạn có thể thêm cờ --mock để chạy demo offline: 'python app/cli.py review --diff evals/dataset/sample.diff --mock'[/dim yellow]")
            sys.exit(1)

    # 1. Hiển thị Hộp Phán Quyết PR
    console.print("\n" + "=" * 75)
    console.print("⚖️  [bold]PHÁN QUYẾT CHO PULL REQUEST[/bold]")
    console.print("=" * 75)

    if report.verdict == ReviewVerdict.REQUEST_CHANGES:
        verdict_panel = Panel(
            f"[bold white on red] 🛑 REQUEST CHANGES — YÊU CẦU SỬA ĐỔI TRƯỚC KHI MERGE [/bold white on red]\n\n"
            f"[bold]Tóm tắt:[/bold] {report.summary}",
            title="[bold red]Phán Quyết[/bold red]",
            border_style="red",
            padding=(1, 2),
        )
    elif report.verdict == ReviewVerdict.APPROVE:
        verdict_panel = Panel(
            f"[bold white on green] ✅ APPROVE — CODE ĐẠT CHUẨN, CHO PHÉP MERGE [/bold white on green]\n\n"
            f"[bold]Tóm tắt:[/bold] {report.summary}",
            title="[bold green]Phán Quyết[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
    else:
        verdict_panel = Panel(
            f"[bold black on yellow] ⚠️  COMMENT — CÓ MỘT SỐ GÓP Ý THAM KHẢO [/bold black on yellow]\n\n"
            f"[bold]Tóm tắt:[/bold] {report.summary}",
            title="[bold yellow]Phán Quyết[/bold yellow]",
            border_style="yellow",
            padding=(1, 2),
        )
    console.print(verdict_panel)

    # 2. Hiển thị Bảng Chi Tiết Findings
    console.print("\n📋 [bold cyan]DANH SÁCH LỖI ĐÃ KIỂM ĐỊNH HỢP LỆ (INLINE FINDINGS):[/bold cyan]")
    if not report.findings:
        console.print("[green]✨ Không phát hiện lỗi nào! Mã nguồn hoàn toàn sạch đẹp.[/green]")
    else:
        table = Table(show_header=True, header_style="bold magenta", expand=True)
        table.add_column("#", width=3, justify="center")
        table.add_column("Vị Trí", style="cyan", width=26)
        table.add_column("Mức Độ", justify="center", width=12)
        table.add_column("Phân Loại", style="dim", width=12)
        table.add_column("Chi Tiết Lỗi & Gợi Ý Sửa Code 1-Click", style="white")

        severity_styles = {
            Severity.CRITICAL: "[bold red]CRITICAL[/bold red]",
            Severity.MAJOR: "[red]MAJOR[/red]",
            Severity.MINOR: "[yellow]MINOR[/yellow]",
            Severity.NIT: "[blue]NIT[/blue]",
        }

        for idx, f in enumerate(report.findings, 1):
            sev_str = severity_styles.get(f.severity, str(f.severity))
            pos_str = f"{f.file}:{f.line}"

            detail_render = Text()
            detail_render.append(f"{f.message}\n", style="white")
            if f.suggestion:
                detail_render.append("\n💡 Gợi ý sửa code (1-click suggestion):\n", style="bold green")
                detail_render.append(f"{f.suggestion}\n", style="italic green")

            table.add_row(str(idx), pos_str, sev_str, f.category.value, detail_render)

        console.print(table)

    # 3. Hiển thị Bảng Kiểm Toán Hiệu Năng (Step Logger Trace)
    summary = logger.get_summary()
    console.print("\n⏱️  [bold cyan]KIỂM TOÁN HIỆU NĂNG & DẤU VẾT HỘP ĐEN (STEP LOG):[/bold cyan]")

    log_table = Table(show_header=True, header_style="bold blue", expand=True)
    log_table.add_column("Bước (Node)", style="white")
    log_table.add_column("Thời Gian (Latency)", justify="right", style="cyan")
    log_table.add_column("Tokens Tiêu Thụ", justify="right", style="magenta")
    log_table.add_column("Trạng Thái", justify="center")

    for rec in logger.records:
        status_styled = "[green]SUCCESS[/green]" if rec.status == "SUCCESS" else "[red]FAILED[/red]"
        token_str = str(rec.token_usage.get("total", 0)) if rec.token_usage.get("total", 0) > 0 else "-"
        log_table.add_row(
            rec.step_name,
            f"{rec.latency_ms:.1f} ms",
            token_str,
            status_styled,
        )

    console.print(log_table)
    console.print(
        f"[dim]• Tổng thời gian: [bold]{summary['total_latency_ms']} ms[/bold] | "
        f"Tổng tokens: [bold]{summary['token_usage']['total']}[/bold] | "
        f"File log: [italic]{logger.log_file.name}[/italic][/dim]\n"
    )

    # 4. Xuất file nếu người dùng yêu cầu
    if out:
        out_path = Path(out)
        out_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        console.print(f"[bold green]💾 Đã lưu báo cáo JSON tại:[/bold green] [white]{out_path.resolve()}[/white]\n")


@cli.command()
def history():
    """Xem danh sách các phiên chạy kiểm toán trong thư mục logs/."""
    render_banner()
    logs_dir = Path("logs")
    if not logs_dir.exists() or not list(logs_dir.glob("*.jsonl")):
        console.print("[yellow]Chưa có phiên chạy nào được ghi lại trong thư mục logs/.[/yellow]")
        return

    table = Table(title="Lịch Sử Các Phiên Chạy (Audit Trace Logs)", header_style="bold cyan")
    table.add_column("Mã Phiên Chạy (Run ID)", style="white")
    table.add_column("Số Bước", justify="right", style="green")
    table.add_column("Dung Lượng Log", justify="right", style="magenta")
    table.add_column("Đường Dẫn File", style="dim")

    for file in sorted(logs_dir.glob("*.jsonl"), reverse=True)[:10]:
        lines = [line for line in file.read_text(encoding="utf-8").splitlines() if line.strip()]
        size_kb = file.stat().st_size / 1024.0
        table.add_row(file.stem, str(len(lines)), f"{size_kb:.1f} KB", str(file.name))

    console.print(table)


@cli.command()
@click.option("--port", "-p", default=5000, type=int, help="Cổng mạng của Web Dashboard (mặc định: 5000)")
@click.option("--no-browser", is_flag=True, default=False, help="Không tự động mở trình duyệt sau khi khởi động")
def web(port: int, no_browser: bool):
    """Khởi động Giao Diện Web Dashboard Trực Quan (Flask + Modern Glassmorphic UI)."""
    render_banner()
    from app.server import start_server
    console.print(f"[bold green]🌐 Đang mở Web Dashboard tại:[/bold green] [cyan]http://127.0.0.1:{port}[/cyan]")
    console.print("[dim]Nhấn Ctrl+C để dừng máy chủ web.[/dim]\n")
    start_server(port=port, open_browser=not no_browser)


if __name__ == "__main__":
    cli()

