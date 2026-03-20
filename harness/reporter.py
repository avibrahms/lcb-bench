"""
LCB results aggregation and scoring.

LCB Score calculation:
  - Per test case: pass=1.0, partial=0.5, fail=0.0, no_data/error/unsupported=excluded
  - Per bias: mean of test case scores (excluding excluded verdicts)
  - Per category: mean of bias scores
  - LCB Score (0-100): mean(VERDICT_WEIGHTS[verdict]) * 100  →  higher = LESS biased = better
"""
from __future__ import annotations

import json
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ResultRecord:
    """Single test case evaluation result."""

    def __init__(
        self,
        test_case_id: str,
        model_id: str,
        bias_id: str,
        bias_name: str,
        category_id: str,
        baseline_response: str | None,
        biased_response: str | None,
        baseline_value: Any,
        biased_value: Any,
        score: float | None,
        verdict: str,
        scoring_details: dict,
        elapsed_s: float = 0.0,
        error: str | None = None,
    ):
        self.test_case_id = test_case_id
        self.model_id = model_id
        self.bias_id = bias_id
        self.bias_name = bias_name
        self.category_id = category_id
        self.baseline_response = baseline_response
        self.biased_response = biased_response
        self.baseline_value = baseline_value
        self.biased_value = biased_value
        self.score = score
        self.verdict = verdict
        self.scoring_details = scoring_details
        self.elapsed_s = elapsed_s
        self.error = error
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "test_case_id": self.test_case_id,
            "model_id": self.model_id,
            "bias_id": self.bias_id,
            "bias_name": self.bias_name,
            "category_id": self.category_id,
            "baseline_value": self.baseline_value,
            "biased_value": self.biased_value,
            "score": self.score,
            "verdict": self.verdict,
            "scoring_details": self.scoring_details,
            "elapsed_s": round(self.elapsed_s, 2),
            "error": self.error,
        }


# Verdict → numeric score mapping. Single source of truth used by all aggregation methods.
# Verdicts not listed here are excluded from LCB Score computation.
VERDICT_WEIGHTS: dict[str, float] = {
    "pass": 1.0,
    "partial": 0.5,
    "fail": 0.0,
}


class RunReport:
    """Aggregated results for a full evaluation run."""

    def __init__(self, model_id: str, results: list[ResultRecord]):
        self.model_id = model_id
        self.results = results
        self.run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # ── LCB Score Computation ────────────────────────────────────────────────

    def lcb_score(self) -> float | None:
        """
        LCB Score (0-100): measures resistance to cognitive biases.
        100 = perfectly unbiased, 0 = maximally biased.
        Excludes no_data, error, and unsupported verdicts from calculation.
        """
        values = [VERDICT_WEIGHTS[r.verdict] for r in self.results if r.verdict in VERDICT_WEIGHTS]
        if not values:
            return None
        return round(statistics.mean(values) * 100, 1)

    def by_bias(self) -> dict[str, dict]:
        """Per-bias scores."""
        groups: dict[str, list[ResultRecord]] = defaultdict(list)
        for r in self.results:
            groups[r.bias_id].append(r)

        out = {}
        for bias_id, recs in groups.items():
            vals = [VERDICT_WEIGHTS[r.verdict] for r in recs if r.verdict in VERDICT_WEIGHTS]
            lcb = round(statistics.mean(vals) * 100, 1) if vals else None

            verdicts = [r.verdict for r in recs]
            out[bias_id] = {
                "bias_name": recs[0].bias_name,
                "lcb_score": lcb,
                "n_cases": len(recs),
                "verdicts": {v: verdicts.count(v) for v in set(verdicts)},
            }
        return out

    def by_category(self) -> dict[str, dict]:
        """Per-category scores."""
        groups: dict[str, list[ResultRecord]] = defaultdict(list)
        for r in self.results:
            groups[r.category_id].append(r)

        out = {}
        for cat_id, recs in groups.items():
            vals = [VERDICT_WEIGHTS[r.verdict] for r in recs if r.verdict in VERDICT_WEIGHTS]
            lcb = round(statistics.mean(vals) * 100, 1) if vals else None

            out[cat_id] = {
                "lcb_score": lcb,
                "n_cases": len(recs),
                "n_biases": len({r.bias_id for r in recs}),
            }
        return out

    # ── Export ────────────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "model_id": self.model_id,
            "lcb_score": self.lcb_score(),
            "n_cases": len(self.results),
            "n_scored": len([r for r in self.results if r.verdict in ("pass", "partial", "fail")]),
            "n_errors": len([r for r in self.results if r.verdict == "error"]),
            "n_no_data": len([r for r in self.results if r.verdict == "no_data"]),
            "by_bias": self.by_bias(),
            "by_category": self.by_category(),
            "results": [r.to_dict() for r in self.results],
        }

    def save(self, output_dir: str | Path) -> Path:
        """Save full results to JSON in output_dir/run_id_model.json."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        model_slug = self.model_id.replace(":", "_").replace("/", "_")
        out_path = output_dir / f"{self.run_id}_{model_slug}.json"
        out_path.write_text(json.dumps(self.to_dict(), indent=2))
        return out_path

    def print_summary(self) -> None:
        """Print a human-readable summary to stdout."""
        lcb = self.lcb_score()
        n = len(self.results)
        print(f"\n{'='*60}")
        print(f"LCB Evaluation Results — {self.model_id}")
        print(f"{'='*60}")
        print(f"LCB Score: {lcb}/100" if lcb is not None else "LCB Score: N/A")
        print(f"Test cases: {n}")

        # Verdict breakdown (all verdict types shown)
        verdicts: dict[str, int] = defaultdict(int)
        for r in self.results:
            verdicts[r.verdict] += 1
        parts = [f"{k}: {verdicts[k]}" for k in ("pass", "partial", "fail", "no_data", "error", "unsupported") if verdicts[k]]
        print("  " + " | ".join(parts) if parts else "  (no results)")

        # Per-category breakdown
        print("\nBy category:")
        for cat_id, info in sorted(self.by_category().items()):
            score_str = f"{info['lcb_score']}/100" if info['lcb_score'] is not None else "N/A"
            print(f"  {cat_id:<40} {score_str:>10}  ({info['n_cases']} cases)")

        # Worst biases
        by_bias = self.by_bias()
        worst = sorted(
            [(k, v) for k, v in by_bias.items() if v["lcb_score"] is not None],
            key=lambda x: x[1]["lcb_score"],
        )[:5]
        if worst:
            print("\nLowest-scoring biases (most affected):")
            for bias_id, info in worst:
                print(f"  {info['bias_name']:<40} {info['lcb_score']}/100")
        print()
