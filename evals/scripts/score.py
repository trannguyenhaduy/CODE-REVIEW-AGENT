"""
evals/scripts/score.py — Script Chấm Tự Động
==============================================
Tính precision, recall, F1 cho kết quả review của agent.

Quy tắc khớp (theo đề tài):
- Cùng `file`
- Dòng nằm trong `line_range` (hoặc lệch tối đa ±3 so với `line`)
- Cùng `category`

Chạy:
    python evals/scripts/score.py --case EC-01
    python evals/scripts/score.py --all
    python evals/scripts/score.py --report
"""
from __future__ import annotations

import sys
sys.stdout.reconfigure(encoding='utf-8')  # Fix UnicodeEncodeError trên Windows cp1252

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from evals.dataset.eval_cases import EVAL_CASES, EvalCase, GroundTruth, get_case_by_id


# ─────────────────────────────────────────────────────────────
# Matching Logic
# ─────────────────────────────────────────────────────────────

LINE_TOLERANCE = 3  # ±3 dòng được chấp nhận

def is_finding_match(
    finding: dict,
    truth: GroundTruth,
) -> bool:
    """
    Kiểm tra một finding có khớp với ground truth không.
    
    Điều kiện (theo quy tắc đề tài):
    1. Cùng file
    2. Dòng trong line_range HOẶC lệch ≤ LINE_TOLERANCE
    3. Cùng category
    """
    # 1. File match (normalize path separators)
    finding_file = finding.get("file", "").replace("\\", "/").lstrip("/")
    truth_file = truth.file.replace("\\", "/").lstrip("/")
    
    if not (finding_file == truth_file or 
            finding_file.endswith(truth_file) or 
            truth_file.endswith(finding_file)):
        return False
    
    # 2. Line match
    finding_line = finding.get("line", 0)
    lo, hi = truth.line_range
    in_range = lo <= finding_line <= hi
    near_center = abs(finding_line - truth.line) <= LINE_TOLERANCE
    
    if not (in_range or near_center):
        return False
    
    # 3. Category match
    finding_category = finding.get("category", "").lower()
    truth_category = truth.category.lower()
    
    if finding_category != truth_category:
        return False
    
    return True


# ─────────────────────────────────────────────────────────────
# Scoring
# ─────────────────────────────────────────────────────────────

@dataclass
class CaseScore:
    """Điểm số cho một eval case."""
    case_id: str
    total_truth: int
    total_findings: int
    true_positives: int
    false_positives: int
    false_negatives: int
    verdict_correct: bool
    matched_pairs: list[tuple] = field(default_factory=list)
    
    @property
    def precision(self) -> float:
        if self.total_findings == 0:
            return 1.0  # Không có finding thì precision undefined → 1.0
        return self.true_positives / self.total_findings
    
    @property
    def recall(self) -> float:
        if self.total_truth == 0:
            return 1.0  # Clean PR: recall undefined → 1.0
        return self.true_positives / self.total_truth
    
    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        if p + r == 0:
            return 0.0
        return 2 * p * r / (p + r)
    
    def summary(self) -> str:
        return (
            f"[{self.case_id}] "
            f"P={self.precision:.2f} R={self.recall:.2f} F1={self.f1:.2f} | "
            f"TP={self.true_positives} FP={self.false_positives} FN={self.false_negatives} | "
            f"Verdict: {'✅' if self.verdict_correct else '❌'}"
        )


@dataclass
class BatchScore:
    """Tổng hợp điểm số cho cả batch cases."""
    case_scores: list[CaseScore]
    
    @property
    def macro_precision(self) -> float:
        scores = [s.precision for s in self.case_scores]
        return sum(scores) / len(scores) if scores else 0.0
    
    @property
    def macro_recall(self) -> float:
        scores = [s.recall for s in self.case_scores]
        return sum(scores) / len(scores) if scores else 0.0
    
    @property
    def macro_f1(self) -> float:
        p, r = self.macro_precision, self.macro_recall
        if p + r == 0:
            return 0.0
        return 2 * p * r / (p + r)
    
    @property
    def micro_precision(self) -> float:
        tp = sum(s.true_positives for s in self.case_scores)
        total_f = sum(s.total_findings for s in self.case_scores)
        return tp / total_f if total_f > 0 else 1.0
    
    @property
    def micro_recall(self) -> float:
        tp = sum(s.true_positives for s in self.case_scores)
        total_t = sum(s.total_truth for s in self.case_scores)
        return tp / total_t if total_t > 0 else 1.0
    
    @property
    def verdict_accuracy(self) -> float:
        return sum(1 for s in self.case_scores if s.verdict_correct) / len(self.case_scores)
    
    @property
    def false_positive_rate_on_clean(self) -> float:
        """Tỷ lệ false positive trên PR sạch (major+ findings trên PR không có lỗi)."""
        clean_scores = [s for s in self.case_scores if s.total_truth == 0]
        if not clean_scores:
            return 0.0
        total_fp = sum(s.false_positives for s in clean_scores)
        return total_fp / len(clean_scores)
    
    def meets_phase1_thresholds(self) -> tuple[bool, list[str]]:
        """
        Kiểm tra đạt ngưỡng Phase 1 theo yêu cầu UC-01:
        - recall ≥ 50%
        - precision ≥ 50%
        - PR sạch ≤ 2 finding major trên bình quân
        """
        issues = []
        
        if self.micro_recall < 0.50:
            issues.append(f"❌ Recall {self.micro_recall:.1%} < 50% (yêu cầu UC-01)")
        
        if self.micro_precision < 0.50:
            issues.append(f"❌ Precision {self.micro_precision:.1%} < 50% (yêu cầu UC-01)")
        
        if self.false_positive_rate_on_clean > 2.0:
            issues.append(
                f"❌ FP rate on clean PR: {self.false_positive_rate_on_clean:.1f} > 2 "
                f"(yêu cầu UC-01: ≤ 2 major findings)"
            )
        
        return len(issues) == 0, issues


def score_case(
    case: EvalCase,
    agent_findings: list[dict],
    agent_verdict: str,
) -> CaseScore:
    """Chấm điểm một case."""
    truth_list = case.ground_truth
    matched_truth = set()
    matched_findings = set()
    matched_pairs = []
    
    # Greedy matching
    for fi, finding in enumerate(agent_findings):
        for ti, truth in enumerate(truth_list):
            if ti in matched_truth:
                continue
            if is_finding_match(finding, truth):
                matched_truth.add(ti)
                matched_findings.add(fi)
                matched_pairs.append((fi, ti))
                break
    
    tp = len(matched_pairs)
    fp = len(agent_findings) - len(matched_findings)
    fn = len(truth_list) - len(matched_truth)
    
    # Verdict check
    verdict_correct = agent_verdict == case.expected_verdict
    # Lỏng hơn: clean PR → approve hoặc comment đều ok
    if case.scenario_type == "clean" and agent_verdict in ("approve", "comment"):
        verdict_correct = True
    
    return CaseScore(
        case_id=case.id,
        total_truth=len(truth_list),
        total_findings=len(agent_findings),
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        verdict_correct=verdict_correct,
        matched_pairs=matched_pairs,
    )


def score_batch(
    results: list[dict],  # List of {"case_id", "findings", "verdict"}
) -> BatchScore:
    """Chấm cả batch kết quả."""
    scores = []
    
    for result in results:
        case = get_case_by_id(result["case_id"])
        if case is None:
            print(f"⚠️ Case không tồn tại: {result['case_id']}")
            continue
        
        score = score_case(
            case=case,
            agent_findings=result.get("findings", []),
            agent_verdict=result.get("verdict", "comment"),
        )
        scores.append(score)
    
    return BatchScore(case_scores=scores)


# ─────────────────────────────────────────────────────────────
# Report Generation
# ─────────────────────────────────────────────────────────────

def print_report(batch: BatchScore) -> None:
    """In báo cáo chi tiết."""
    print("\n" + "=" * 70)
    print("📊 KẾT QUẢ EVAL — CODE REVIEW AGENT (Phase 1 UC-01)")
    print("=" * 70)
    
    print("\n📋 Chi tiết từng case:")
    for s in batch.case_scores:
        print(f"  {s.summary()}")
    
    print("\n📈 Tổng hợp (Micro):")
    print(f"  Precision: {batch.micro_precision:.1%}")
    print(f"  Recall:    {batch.micro_recall:.1%}")
    print(f"  Verdict Accuracy: {batch.verdict_accuracy:.1%}")
    print(f"  FP rate on clean PRs: {batch.false_positive_rate_on_clean:.1f} major findings/PR")
    
    print("\n🎯 Ngưỡng Phase 1 (UC-01):")
    passed, issues = batch.meets_phase1_thresholds()
    if passed:
        print("  ✅ ĐẠT TẤT CẢ YÊU CẦU PHASE 1")
    else:
        for issue in issues:
            print(f"  {issue}")
    
    print("=" * 70)


# ─────────────────────────────────────────────────────────────
# Dry Run với Mock Data (để test script)
# ─────────────────────────────────────────────────────────────

def dry_run_demo() -> None:
    """Demo script với kết quả giả để test pipeline eval."""
    print("🔵 Dry Run Demo — Script chấm tự động")
    print("(Chạy với kết quả giả để kiểm tra pipeline eval)\n")
    
    # Giả lập kết quả agent trả về
    mock_results = [
        {
            "case_id": "EC-01",
            "verdict": "request_changes",
            "findings": [
                {
                    "file": "app/services/booking.py",
                    "line": 43,
                    "category": "logic",
                    "severity": "major",
                    "message": "Đổi >= thành <= làm đảo ngược logic kiểm tra sức chứa",
                    "confidence": 0.95,
                }
            ]
        },
        {
            "case_id": "EC-02",
            "verdict": "request_changes",
            "findings": [
                {
                    "file": "app/api/search.py",
                    "line": 17,
                    "category": "security",
                    "severity": "critical",
                    "message": "SQL injection qua f-string",
                    "confidence": 0.99,
                }
            ]
        },
        {
            "case_id": "EC-04",
            "verdict": "approve",
            "findings": []  # PR sạch → không có findings
        },
        {
            "case_id": "EC-11",
            "verdict": "request_changes",  # Agent đã bỏ qua prompt injection
            "findings": [
                {
                    "file": "app/api/payments.py",
                    "line": 20,
                    "category": "security",
                    "severity": "critical",
                    "message": "SQL injection: card_number không được sanitize",
                    "confidence": 0.98,
                }
            ]
        },
    ]
    
    batch = score_batch(mock_results)
    print_report(batch)
    
    # Export JSON
    output = {
        "micro_precision": batch.micro_precision,
        "micro_recall": batch.micro_recall,
        "verdict_accuracy": batch.verdict_accuracy,
        "cases": [
            {
                "id": s.case_id,
                "precision": s.precision,
                "recall": s.recall,
                "f1": s.f1,
                "tp": s.true_positives,
                "fp": s.false_positives,
                "fn": s.false_negatives,
            }
            for s in batch.case_scores
        ]
    }
    
    output_path = Path("evals/results/phase1_demo_score.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Kết quả lưu tại: {output_path}")


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Eval Scoring Script — Code Review Agent")
    parser.add_argument("--case", help="Chấm một case cụ thể (ví dụ: EC-01)")
    parser.add_argument("--all", action="store_true", help="Chấm tất cả cases")
    parser.add_argument("--demo", action="store_true", help="Dry run với kết quả giả")
    parser.add_argument("--input", help="File JSON chứa kết quả agent")
    args = parser.parse_args()
    
    if args.demo:
        dry_run_demo()
    elif args.input:
        with open(args.input, encoding="utf-8") as f:
            results = json.load(f)
        batch = score_batch(results)
        print_report(batch)
    else:
        # List available cases
        print("📋 Bộ Eval Dataset Phase 1:")
        print(f"  Tổng: {len(EVAL_CASES)} cases")
        for c in EVAL_CASES:
            bug_count = len(c.ground_truth)
            print(f"  [{c.id}] {c.scenario_type.upper():6s} | bugs={bug_count} | {c.description[:60]}")
        print("\nDùng --demo để chạy dry run, hoặc --input <file.json> để chấm kết quả thực")
