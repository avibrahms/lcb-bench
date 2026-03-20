# LCB Evaluation Harness v0.1

Python framework for running LLM Cognitive Bias Benchmark evaluations.

See the [main README](../README.md) for full documentation.

## Architecture

```
harness/
  loaders.py      -- Load & parse test case JSON files
  models.py       -- LLM adapters (Anthropic, OpenAI, Gemini)
  extractors.py   -- Extract signals from model responses
  scorers.py      -- Scoring methods (anchor_pull_index, binary_choice, etc.)
  runner.py       -- Orchestration: run baseline + biased, score, collect results
  reporter.py     -- Aggregate into LCB score, save JSON, print summary
  cli.py          -- Command-line interface
```

## Usage

```bash
# From the repository root:
python3 -m harness run \
  --test-cases data/ \
  --model anthropic:claude-haiku-4-5-20251001 \
  --output-dir results/

# Dry run (no API calls)
python3 -m harness dry-run \
  --test-cases data/ \
  --model anthropic:claude-haiku-4-5-20251001

# Re-score existing results
python3 -m harness score results/20260316_205526_gpt-4o-mini.json

# Re-run failed cases from a previous run
python3 -m harness rerun-failed results/previous_run.json \
  --test-cases data/ \
  --model openai:gpt-4o-mini \
  --output-dir results/
```

## LCB Score

- **Range:** 0 to 100 (higher = less biased)
- **Calculation:** mean(pass=1.0, partial=0.5, fail=0.0) x 100
- **Excludes:** cases where extraction failed (no_data) or errored
