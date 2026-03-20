"""
LCB Evaluation Runner — main orchestration logic.

Usage (programmatic):
    from lcb_harness.runner import run_evaluation
    from lcb_harness.models import get_adapter

    adapter = get_adapter("anthropic:claude-haiku-4-5-20251001")
    report = run_evaluation(
        test_cases_path="specs/example-test-cases.json",
        model=adapter,
        output_dir="results/",
    )
    report.print_summary()
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .extractors import extract
from .loaders import TestCase, load_test_cases
from .models import ModelAdapter
from .reporter import ResultRecord, RunReport
from .scorers import score

# Scorers that do keyword matching on full response text (need raw text, not category labels).
# All other scorers do string/numeric comparison and need extracted values.
_KEYWORD_SCORERS = {"evidence_balance_ratio", "correlation_check", "attribution_coding"}


_CHECKPOINT_EVERY = 25  # Save partial results every N cases


def run_evaluation(
    test_cases_path: str | Path,
    model: ModelAdapter,
    output_dir: str | Path | None = None,
    *,
    judge: ModelAdapter | None = None,
    verbose: bool = True,
    dry_run: bool = False,
    case_filter: set[str] | None = None,
    resume_from: str | Path | None = None,
) -> RunReport:
    """
    Run a full LCB evaluation on the given model.

    Args:
        test_cases_path: Path to a test case JSON file or directory.
        model: The model adapter to evaluate.
        output_dir: If given, save results there. None = don't save.
        judge: Optional cheaper model used for free_text_coded extraction.
               Defaults to same model as evaluated model.
        verbose: Print progress to stdout.
        dry_run: Skip actual API calls (returns None for all responses). For testing.
        resume_from: Path to a checkpoint JSON to resume from (skips already-completed cases).

    Returns:
        RunReport with all results and LCB score.
    """
    test_cases = load_test_cases(test_cases_path)
    if case_filter:
        test_cases = [tc for tc in test_cases if tc.id in case_filter]
        if not test_cases:
            print(f"Warning: case_filter had {len(case_filter)} IDs but none matched loaded test cases.")

    # Resume: load checkpoint and skip already-completed cases
    completed_results: list[ResultRecord] = []
    completed_ids: set[str] = set()
    if resume_from:
        ckpt_path = Path(resume_from)
        if ckpt_path.exists():
            ckpt_data = json.loads(ckpt_path.read_text())
            for r in ckpt_data.get("results", []):
                completed_ids.add(r["test_case_id"])
                completed_results.append(ResultRecord(
                    test_case_id=r["test_case_id"],
                    model_id=r["model_id"],
                    bias_id=r["bias_id"],
                    bias_name=r["bias_name"],
                    category_id=r["category_id"],
                    baseline_response=None,
                    biased_response=None,
                    baseline_value=r.get("baseline_value"),
                    biased_value=r.get("biased_value"),
                    score=r.get("score"),
                    verdict=r.get("verdict", "error"),
                    scoring_details=r.get("scoring_details", {}),
                    elapsed_s=r.get("elapsed_s", 0),
                ))
            if verbose:
                print(f"Resumed from checkpoint: {len(completed_ids)} cases already done")

    remaining = [tc for tc in test_cases if tc.id not in completed_ids]
    total = len(test_cases)

    if verbose:
        print(f"Loaded {total} test cases from {test_cases_path}")
        if completed_ids:
            print(f"Skipping {len(completed_ids)} completed, running {len(remaining)}")
        print(f"Evaluating model: {model.model_id}")

    # Use same model as judge if none provided
    effective_judge = judge or model
    results: list[ResultRecord] = list(completed_results)

    # Checkpoint path
    ckpt_out = None
    if output_dir:
        ckpt_dir = Path(output_dir)
        ckpt_dir.mkdir(parents=True, exist_ok=True)
        model_slug = model.model_id.replace(":", "_").replace("/", "_")
        ckpt_out = ckpt_dir / f"_checkpoint_{model_slug}.json"

    done_count = len(completed_ids)
    for i, tc in enumerate(remaining, 1):
        done_count += 1
        if verbose:
            print(f"  [{done_count}/{total}] {tc.id} ({tc.bias_name}) ...", end=" ", flush=True)

        start = time.perf_counter()
        try:
            result = _evaluate_one(tc, model, effective_judge, dry_run=dry_run)
        except Exception as exc:
            elapsed = time.perf_counter() - start
            result = ResultRecord(
                test_case_id=tc.id,
                model_id=model.model_id,
                bias_id=tc.bias_id,
                bias_name=tc.bias_name,
                category_id=tc.category_id,
                baseline_response=None,
                biased_response=None,
                baseline_value=None,
                biased_value=None,
                score=None,
                verdict="error",
                scoring_details={},
                elapsed_s=elapsed,
                error=str(exc),
            )

        elapsed = time.perf_counter() - start
        result.elapsed_s = elapsed
        results.append(result)

        # Checkpoint every N cases
        if ckpt_out and i % _CHECKPOINT_EVERY == 0:
            _save_checkpoint(ckpt_out, model.model_id, results)

        # Pace API calls to avoid rate limiting (Vertex AI free tier).
        # Each test case makes up to 4 calls (baseline + biased + 2 judge).
        if not dry_run and elapsed < 12.0:
            time.sleep(12.0 - elapsed)

        if verbose:
            verdict_symbol = {"pass": "✓", "partial": "~", "fail": "✗", "error": "!", "no_data": "?"}.get(
                result.verdict, "?"
            )
            score_str = f"{result.score:.3f}" if result.score is not None else "N/A"
            print(f"{verdict_symbol} score={score_str} ({elapsed:.1f}s)")

    report = RunReport(model_id=model.model_id, results=results)

    if output_dir is not None:
        saved_path = report.save(output_dir)
        if verbose:
            print(f"\nResults saved to: {saved_path}")
        # Clean up checkpoint
        if ckpt_out and ckpt_out.exists():
            ckpt_out.unlink()

    return report


def _save_checkpoint(path: Path, model_id: str, results: list[ResultRecord]) -> None:
    """Save partial results as a checkpoint file (atomic write)."""
    data = {
        "model_id": model_id,
        "n_completed": len(results),
        "results": [r.to_dict() for r in results],
    }
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data))
    tmp.replace(path)


def _evaluate_one(
    tc: TestCase,
    model: ModelAdapter,
    judge: ModelAdapter,
    *,
    dry_run: bool,
) -> ResultRecord:
    """Evaluate a single test case and return a ResultRecord."""
    extraction_spec = tc.scoring.get("output_extraction", {})
    ext_type = extraction_spec.get("type")
    ext_prompt = extraction_spec.get("extraction_prompt")
    ext_regex = extraction_spec.get("extraction_regex")
    ext_range = extraction_spec.get("valid_range")
    ext_cats = extraction_spec.get("categories")

    def run_prompt(turns: list[dict]) -> tuple[str, Any]:
        """Run prompt and extract value. Returns (raw_response, extracted_value)."""
        if dry_run:
            return "[DRY RUN]", None
        raw = model.complete(_convert_turns(turns))
        # For free_text_coded that needs follow-up extraction, run extraction prompt
        if ext_type == "free_text_coded" and ext_prompt:
            extracted = extract(
                raw,
                ext_type,
                extraction_prompt=ext_prompt,
                extraction_regex=ext_regex,
                valid_range=ext_range,
                categories=ext_cats,
                judge=judge,
            )
        elif ext_type == "free_text_coded" and not ext_prompt:
            # Keyword-matching scorers need full response text to find signals.
            # String-comparison scorers need short category labels via LLM judge.
            if tc.scoring_method in _KEYWORD_SCORERS:
                extracted = raw
            else:
                extracted = extract(
                    raw,
                    ext_type,
                    extraction_prompt=ext_prompt,
                    extraction_regex=ext_regex,
                    valid_range=ext_range,
                    categories=ext_cats,
                    judge=judge,
                )
        else:
            extracted = extract(
                raw,
                ext_type,
                extraction_prompt=ext_prompt,
                extraction_regex=ext_regex,
                valid_range=ext_range,
                categories=ext_cats,
                judge=judge,
            )
        return raw, extracted

    # Run baseline and biased conditions
    baseline_raw, baseline_val = run_prompt(tc.baseline_turns)
    biased_raw, biased_val = run_prompt(tc.biased_turns)

    # Score
    scored = score(
        method=tc.scoring_method,
        baseline_value=baseline_val,
        biased_value=biased_val,
        criteria=tc.criteria,
    )

    return ResultRecord(
        test_case_id=tc.id,
        model_id=model.model_id,
        bias_id=tc.bias_id,
        bias_name=tc.bias_name,
        category_id=tc.category_id,
        baseline_response=baseline_raw,
        biased_response=biased_raw,
        baseline_value=baseline_val,
        biased_value=biased_val,
        score=scored.get("score"),
        verdict=scored.get("verdict", "error"),
        scoring_details=scored.get("details", {}),
    )


def merge_results(prev_data: dict, new_report: RunReport) -> list[ResultRecord]:
    """Merge new results into previous run data, replacing no_data/error cases."""
    # Build lookup of new results by test_case_id
    new_by_id = {r.test_case_id: r for r in new_report.results}

    merged = []
    for prev in prev_data.get("results", []):
        tc_id = prev["test_case_id"]
        if tc_id in new_by_id:
            # Use new result (re-run)
            merged.append(new_by_id[tc_id])
        else:
            # Keep previous result
            merged.append(ResultRecord(
                test_case_id=prev["test_case_id"],
                model_id=prev["model_id"],
                bias_id=prev["bias_id"],
                bias_name=prev["bias_name"],
                category_id=prev["category_id"],
                baseline_response=None,
                biased_response=None,
                baseline_value=prev.get("baseline_value"),
                biased_value=prev.get("biased_value"),
                score=prev.get("score"),
                verdict=prev.get("verdict", "error"),
                scoring_details=prev.get("scoring_details", {}),
                elapsed_s=prev.get("elapsed_s", 0),
            ))
    return merged


def _convert_turns(turns: list[dict]) -> list[dict[str, str]]:
    """Convert test case turns to the messages format expected by model adapters."""
    return [{"role": t["role"], "content": t["content"]} for t in turns]
