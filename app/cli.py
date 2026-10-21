"""
app/cli.py — CLI Interface cho Code Review Agent (Phase 1)
===========================================================
Giao diện dòng lệnh cho UC-01: review PR từ local diff file hoặc stdin.

Sử dụng:
    python app/cli.py review --diff path/to/pr.diff --pr 42
    python app/cli.py review --diff - --pr 42 < my.diff  (stdin)
    python app/cli.py eval --demo
    python app/cli.py info
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Fix Windows cp1252 UnicodeEncodeError (Lesson #1)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import click
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import print as rprint
    RICH_AVAILABLE = True
    console = Console(force_terminal=True, legacy_windows=False)
except ImportError:
    RICH_AVAILABLE = False
    console = None
    print("⚠️ Thiếu rich/click: pip install rich click")

from agent.tools.git_diff_reader import GitDiffReader
from agent.harness.validator import FindingValidator
from evals.dataset.eval_cases import EVAL_CASES, print_summary




def print_finding(finding: dict, index: int) -> None:
    """In một finding với màu theo severity."""
    severity_colors = {
        "critical": "bold red",
        "major": "red",
        "minor": "yellow",
        "nit": "dim",
    }
    severity = finding.get("severity", "minor")
    color = severity_colors.get(severity, "white")
    
    if console:
        console.print(
            f"\n[{color}]#{index + 1} [{severity.upper()}][/{color}] "
            f"[bold]{finding.get('file', '?')}:{finding.get('line', '?')}[/bold] "
            f"({finding.get('category', '?')})"
        )
        console.print(f"  {finding.get('message', '')}")
        if finding.get("suggestion"):
            console.print("  [dim]Suggestion:[/dim]")
            console.print(f"  [green]{finding['suggestion'][:200]}[/green]")
        if finding.get("confidence"):
            console.print(f"  [dim]confidence: {finding['confidence']:.0%}[/dim]")
    else:
        print(f"\n#{index + 1} [{severity.upper()}] {finding.get('file')}:{finding.get('line')}")
        print(f"  {finding.get('message')}")


@click.group()
def cli():
    """🤖 Code Review Agent — SE373 Đồ án cuối kỳ"""
    pass


@cli.command()
@click.option("--diff", "diff_path", required=True, 
              help="Đường dẫn file diff (dùng '-' để đọc từ stdin)")
@click.option("--pr", "pr_number", type=int, default=0, 
              help="Số PR (dùng để sinh run_id)")
@click.option("--repo", default="unknown/repo", 
              help="Tên repo (owner/repo)")
@click.option("--sha", "commit_sha", default="HEAD", 
              help="Commit SHA")
@click.option("--repo-root", default=".", 
              help="Đường dẫn local repo (để đọc file context)")
@click.option("--output", "output_path", default=None,
              help="File JSON để lưu kết quả review")
@click.option("--dry-run", is_flag=True, 
              help="Chỉ parse diff, không gọi LLM")
def review(diff_path, pr_number, repo, commit_sha, repo_root, output_path, dry_run):
    """Review một PR từ file diff hoặc stdin."""
    
    # Đọc diff
    if diff_path == "-":
        diff_text = sys.stdin.read()
    else:
        path = Path(diff_path)
        if not path.exists():
            click.echo(f"❌ File không tồn tại: {diff_path}", err=True)
            sys.exit(1)
        diff_text = path.read_text(encoding="utf-8")
    
    if not diff_text.strip():
        click.echo("❌ Diff rỗng", err=True)
        sys.exit(1)
    
    # Parse diff để hiển thị info
    reader = GitDiffReader()
    parsed = reader.parse(diff_text)
    summary = reader.get_summary(parsed)
    
    if console:
        console.print(Panel(
            f"[bold]PR:[/] #{pr_number}\n"
            f"[bold]Repo:[/] {repo}\n"
            f"[bold]SHA:[/] {commit_sha[:8]}\n"
            f"[bold]Files changed:[/] {summary['total_files']}\n"
            f"[bold]Lines added:[/] {summary['total_added_lines']} | "
            f"[bold]Lines removed:[/] {summary['total_removed_lines']}",
            title="🔍 Code Review Agent — Phase 1",
            border_style="blue",
        ))
        
        if summary["files"]:
            t = Table(title="Changed Files")
            t.add_column("File", style="cyan")
            t.add_column("Status")
            for f in parsed.files:
                status = "🆕 NEW" if f.is_new_file else ("🗑️ DELETED" if f.is_deleted_file else "✏️ MODIFIED")
                t.add_row(f.path, status)
            console.print(t)
    
    if dry_run:
        click.echo("\n✅ Dry run hoàn thành — bỏ qua LLM call")
        return
    
    # Run agent
    click.echo("\n🤖 Đang chạy agent review...")
    
    try:
        from agent.graph import run_review
        result = run_review(
            pr_number=pr_number,
            diff_text=diff_text,
            repo=repo,
            commit_sha=commit_sha,
            repo_root=repo_root,
            verbose=True,
        )
    except Exception as e:
        click.echo(f"❌ Agent error: {e}", err=True)
        # Fallback: parse-only mode
        result = {
            "verdict": "comment",
            "findings": [],
            "error": str(e),
            "pr_number": pr_number,
        }
    
    # Display results
    findings = result.get("findings", [])
    verdict = result.get("verdict", "comment")
    
    verdict_style = {
        "approve": "✅ APPROVE",
        "comment": "💬 COMMENT",
        "request_changes": "🚫 REQUEST CHANGES",
    }.get(verdict, verdict.upper())
    
    if console:
        console.print(f"\n[bold]Verdict:[/] {verdict_style}")
        console.print(f"[bold]Findings:[/] {len(findings)}")
    
    for i, finding in enumerate(findings):
        print_finding(finding, i)
    
    if result.get("error"):
        click.echo(f"\n⚠️ Errors: {result['error']}", err=True)
    
    # Save output
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        click.echo(f"\n💾 Kết quả lưu tại: {output_path}")
    
    click.echo(f"\n📝 Trace: {result.get('trace_path', 'N/A')}")


@cli.command()
@click.option("--demo", is_flag=True, help="Chạy dry run với kết quả giả")
@click.option("--input", "input_path", default=None, 
              help="File JSON kết quả agent để chấm")
def eval_score(demo, input_path):
    """Chấm điểm eval — tính precision/recall/F1."""
    
    if demo:
        from evals.scripts.score import dry_run_demo
        dry_run_demo()
    elif input_path:
        from evals.scripts.score import score_batch, print_report
        with open(input_path, encoding="utf-8") as f:
            results = json.load(f)
        batch = score_batch(results)
        print_report(batch)
    else:
        print_summary()
        click.echo("\nDùng --demo để chạy dry run")


@cli.command()
def info():
    """Hiển thị thông tin dự án và trạng thái."""
    if console:
        console.print(Panel(
            "[bold]SE373 — Đề tài 02: Code Review Agent[/]\n"
            "[dim]Kỹ thuật xây dựng hệ thống Agentic AI — UIT[/]\n\n"
            "[bold]Kiến trúc:[/] LangGraph ReAct + Pydantic v2 Structured Output\n"
            "[bold]Model:[/] GPT-4o-mini (configurable via .env)\n"
            "[bold]Tools:[/] GitDiffReader, FileContextReader, StaticAnalysis\n\n"
            "[bold]Use Cases (Phase 1):[/]\n"
            "  ✅ UC-01: Phân tích diff, comment inline, severity, suggestion\n"
            "  ⏳ UC-02: RAG + quy ước nhóm (Phase 2)\n"
            "  ⏳ UC-04: Multi-agent reviewer (Phase 3)\n",
            title="🤖 Code Review Agent v0.1.0",
            border_style="blue",
        ))
    else:
        print("Code Review Agent v0.1.0 — SE373")
    
    # Check dependencies
    deps = {
        "langchain": False,
        "langgraph": False,
        "unidiff": False,
        "pydantic": False,
        "rich": False,
        "dotenv": False,
    }
    
    for dep in deps:
        try:
            __import__(dep.replace("-", "_"))
            deps[dep] = True
        except ImportError:
            pass
    
    if console:
        t = Table(title="Dependencies")
        t.add_column("Package")
        t.add_column("Status")
        for pkg, installed in deps.items():
            status = "[green]✅ Installed[/]" if installed else "[red]❌ Missing[/]"
            t.add_row(pkg, status)
        console.print(t)
    
    missing = [k for k, v in deps.items() if not v]
    if missing:
        click.echo(f"\n⚠️ Cài thiếu: pip install {' '.join(missing)}")
    else:
        click.echo("\n✅ Tất cả dependencies đã được cài")


if __name__ == "__main__":
    cli()
