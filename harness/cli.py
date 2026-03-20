"""
LCB Harness CLI — run evaluations from the command line.

Usage:
    python -m lcb_harness run \
        --test-cases specs/example-test-cases.json \
        --model anthropic:claude-haiku-4-5-20251001 \
        --output-dir results/

    python -m lcb_harness run \
        --test-cases specs/ \
        --model anthropic:claude-sonnet-4-6 \
        --judge anthropic:claude-haiku-4-5-20251001 \
        --output-dir results/ \
        --verbose

    python -m lcb_harness dry-run \
        --test-cases specs/example-test-cases.json \
        --model anthropic:claude-haiku-4-5-20251001
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m lcb_harness",
        description="LLM Cognitive Bias Benchmark — evaluation harness",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── run command ───────────────────────────────────────────────────────────
    run_p = sub.add_parser("run", help="Run a full evaluation")
    run_p.add_argument("--test-cases", required=True, help="Path to test case JSON file or directory")
    run_p.add_argument("--model", required=True, help="Model spec (e.g. anthropic:claude-haiku-4-5-20251001)")
    run_p.add_argument("--judge", default=None, help="Judge model for free-text extraction (default: same as model)")
    run_p.add_argument("--output-dir", default=None, help="Directory to save results JSON")
    run_p.add_argument("--verbose", action="store_true", default=True, help="Print progress (default: on)")
    run_p.add_argument("--quiet", action="store_true", help="Suppress progress output")
    run_p.add_argument("--resume", default=None, help="Resume from a checkpoint file (skips completed cases)")

    # ── dry-run command ───────────────────────────────────────────────────────
    dry_p = sub.add_parser("dry-run", help="Test harness without API calls")
    dry_p.add_argument("--test-cases", required=True, help="Path to test case JSON file or directory")
    dry_p.add_argument("--model", default="anthropic:claude-haiku-4-5-20251001", help="Model spec")

    # ── rerun-failed command ──────────────────────────────────────────────────
    rerun_p = sub.add_parser("rerun-failed", help="Re-run only no_data/error cases from a previous run")
    rerun_p.add_argument("results_file", help="Path to previous results JSON file")
    rerun_p.add_argument("--test-cases", required=True, help="Path to test case JSON file or directory")
    rerun_p.add_argument("--model", required=True, help="Model spec (must match original run)")
    rerun_p.add_argument("--judge", default=None, help="Judge model for free-text extraction")
    rerun_p.add_argument("--output-dir", default=None, help="Directory to save merged results JSON")
    rerun_p.add_argument("--quiet", action="store_true", help="Suppress progress output")

    # ── score command (score existing results file) ───────────────────────────
    score_p = sub.add_parser("score", help="Re-score an existing results JSON file")
    score_p.add_argument("results_file", help="Path to results JSON file")

    args = parser.parse_args()

    if args.command == "run":
        _cmd_run(args)
    elif args.command == "dry-run":
        _cmd_dryrun(args)
    elif args.command == "rerun-failed":
        _cmd_rerun_failed(args)
    elif args.command == "score":
        _cmd_score(args)


def _cmd_run(args) -> None:
    from .models import get_adapter
    from .runner import run_evaluation

    verbose = not args.quiet

    model = get_adapter(args.model)
    judge = get_adapter(args.judge) if args.judge else None

    # Auto-detect checkpoint for resume
    resume_path = args.resume
    if not resume_path and args.output_dir:
        from pathlib import Path as _P
        model_slug = args.model.split(":", 1)[-1].replace("/", "_") if ":" in args.model else args.model
        auto_ckpt = _P(args.output_dir) / f"_checkpoint_{model_slug}.json"
        if auto_ckpt.exists():
            resume_path = str(auto_ckpt)
            print(f"Auto-resuming from checkpoint: {auto_ckpt}")

    report = run_evaluation(
        test_cases_path=args.test_cases,
        model=model,
        output_dir=args.output_dir,
        judge=judge,
        verbose=verbose,
        resume_from=resume_path,
    )
    report.print_summary()

    # Exit code: 0 if LCB score >= 50 (model resists bias), else 1
    # lcb is None means all cases errored — that's a failure
    lcb = report.lcb_score()
    sys.exit(0 if lcb is not None and lcb >= 50 else 1)


def _cmd_dryrun(args) -> None:
    from .models import get_adapter
    from .runner import run_evaluation

    model = get_adapter(args.model)
    report = run_evaluation(
        test_cases_path=args.test_cases,
        model=model,
        verbose=True,
        dry_run=True,
    )
    report.print_summary()
    print("Dry run complete. No API calls were made.")


def _cmd_rerun_failed(args) -> None:
    import json
    from .models import get_adapter
    from .runner import run_evaluation, merge_results

    prev_path = Path(args.results_file)
    if not prev_path.exists():
        print(f"Error: {prev_path} not found", file=sys.stderr)
        sys.exit(1)

    prev_data = json.loads(prev_path.read_text())
    failed_ids = {
        r["test_case_id"]
        for r in prev_data.get("results", [])
        if r.get("verdict") in ("no_data", "error")
    }
    if not failed_ids:
        print("No failed cases to re-run.")
        sys.exit(0)

    # Validate model matches original run
    orig_model = prev_data.get("model_id", "")
    spec_model = args.model.split(":", 1)[-1] if ":" in args.model else args.model
    if orig_model and spec_model != orig_model:
        print(f"Warning: --model '{spec_model}' differs from original run model '{orig_model}'", file=sys.stderr)

    print(f"Found {len(failed_ids)} failed cases to re-run.")
    verbose = not args.quiet
    model = get_adapter(args.model)
    judge = get_adapter(args.judge) if args.judge else None

    report = run_evaluation(
        test_cases_path=args.test_cases,
        model=model,
        output_dir=None,  # don't save intermediate
        judge=judge,
        verbose=verbose,
        case_filter=failed_ids,
    )

    # Merge new results into previous
    merged = merge_results(prev_data, report)
    from .reporter import RunReport, ResultRecord
    merged_report = RunReport(model_id=prev_data["model_id"], results=merged)

    if args.output_dir:
        saved_path = merged_report.save(args.output_dir)
        print(f"\nMerged results saved to: {saved_path}")

    merged_report.print_summary()
    lcb = merged_report.lcb_score()
    sys.exit(0 if lcb is not None and lcb >= 50 else 1)


def _cmd_score(args) -> None:
    import json
    from .reporter import ResultRecord, RunReport

    path = Path(args.results_file)
    if not path.exists():
        print(f"Error: {path} not found", file=sys.stderr)
        sys.exit(1)

    data = json.loads(path.read_text())
    results = []
    for r in data.get("results", []):
        results.append(ResultRecord(
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

    report = RunReport(model_id=data.get("model_id", "unknown"), results=results)
    report.print_summary()


if __name__ == "__main__":
    main()
