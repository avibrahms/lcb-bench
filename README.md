# LCB-Bench: Large-scale Cognitive Bias Benchmark for LLMs

LCB-Bench is an open-source evaluation framework for measuring **cognitive biases** in Large Language Model outputs. It provides 1,500 human-authored test cases across 30 cognitive biases organized in 7 categories, a Python evaluation harness, and a standardized LCB Score for cross-model comparison.

Unlike existing benchmarks that focus on social and discrimination biases (BBQ, CrowS-Pairs, BOLD), LCB measures how AI systems *think*: anchoring on irrelevant numbers, succumbing to framing effects, exhibiting sunk cost reasoning, and more. These cognitive biases directly affect the quality of AI-generated advice, analysis, and decisions in high-stakes domains like medicine, law, and finance.

**Paper:** *LCB: A 1,500-Case Benchmark for Measuring Cognitive Biases in Large Language Model Outputs* (Pilcer, 2026). Preprint forthcoming on arXiv. Target venue: AIES 2026.

## Taxonomy

LCB organizes 30 cognitive biases (from a full taxonomy of 72) into 7 categories:

| Category | Biases | Test Cases | Description |
|----------|--------|------------|-------------|
| Decision-Making | 8 | 400 | Sunk cost, framing, loss aversion, status quo, omission, zero-risk, confirmation, planning fallacy |
| Judgment & Estimation | 5 | 250 | Anchoring, focalism, overconfidence, Dunning-Kruger, insufficient adjustment |
| Probability & Statistical | 6 | 300 | Gambler's fallacy, conjunction fallacy, base rate neglect, availability heuristic, hot hand, sample size insensitivity |
| Social Cognition | 4 | 200 | Bandwagon effect, authority bias, halo effect, fundamental attribution error |
| LLM-Specific | 3 | 150 | Sycophancy, position bias, verbosity bias |
| Information Processing | 2 | 100 | Conservatism bias, salience bias |
| Memory & Recall | 2 | 100 | Primacy effect, recency effect |
| **Total** | **30** | **1,500** | |

Each test case includes a **baseline** prompt (no bias trigger) and a **biased** prompt (with a specific cognitive bias trigger inserted). The LCB Score measures how much the model's output shifts between conditions.

## Results

Three frontier models fully evaluated on all 1,500 test cases (March 2026):

| Model | Provider | LCB Score | Valid Scores | Strongest Category | Weakest Category |
|-------|----------|-----------|--------------|-------------------|-----------------|
| GPT-4o-mini | OpenAI | **80.3** | 1,487/1,500 | Judgment & Estimation (90.3) | Memory & Recall (57.0) |
| Gemini 2.5 Flash | Google | **77.1** | 1,388/1,500 | Decision-Making (89.7) | Memory & Recall (47.9) |
| Claude Sonnet 4.6 | Anthropic | **69.0** | 1,479/1,500 | Decision-Making (81.7) | Memory & Recall (47.0) |

**LCB Score** ranges 0 to 100. Higher scores indicate greater resistance to cognitive biases (less biased). A score of 100 means the model's outputs are completely unaffected by bias triggers.

### Key Findings

1. **General capability does not predict bias resistance.** Claude Sonnet 4.6, widely considered more capable than GPT-4o-mini on standard benchmarks, scores 11.3 points lower on LCB.
2. **Universal weaknesses exist.** All models score below 60 on Memory & Recall. Primacy and recency effects systematically influence outputs across all providers.
3. **Universal strengths exist.** All models achieve near-perfect scores on Framing Effect (100.0) and Base Rate Neglect (100.0). Current RLHF training effectively mitigates explicit logical framing biases.
4. **Bias profiles are model-specific.** Claude Sonnet is uniquely susceptible to Salience Bias (14.0 vs. 54+ for others). Gemini Flash is uniquely weak on Gambler's Fallacy (44.4 vs. 56+ for others).

## Quick Start

### Installation

```bash
git clone https://github.com/avibrahms/lcb-bench.git
cd lcb-bench
pip install -r requirements.txt
```

### Set API Keys

You need at least one provider's API key:

```bash
export ANTHROPIC_API_KEY=sk-ant-...    # For Claude models
export OPENAI_API_KEY=sk-...           # For GPT models
export GEMINI_API_KEY=...              # For Gemini models (free key from aistudio.google.com)
```

### Run an Evaluation

```bash
# Dry run (validates setup, no API calls)
python3 -m harness dry-run \
  --test-cases data/ \
  --model anthropic:claude-haiku-4-5-20251001

# Evaluate a model on all 1,500 test cases
python3 -m harness run \
  --test-cases data/ \
  --model openai:gpt-4o-mini \
  --output-dir results/

# Evaluate with a separate judge model for free-text extraction
python3 -m harness run \
  --test-cases data/ \
  --model anthropic:claude-sonnet-4-6 \
  --judge anthropic:claude-haiku-4-5-20251001 \
  --output-dir results/

# Re-score an existing results file
python3 -m harness score results/20260316_205526_gpt-4o-mini.json
```

### Supported Models

| Spec | Provider | Notes |
|------|----------|-------|
| `anthropic:claude-haiku-4-5-20251001` | Anthropic | Fast, cheap. Ideal for bulk evals and as judge model |
| `anthropic:claude-sonnet-4-6` | Anthropic | Mid-range quality |
| `openai:gpt-4o-mini` | OpenAI | Requires `pip install openai` |
| `openai:gpt-4o` | OpenAI | Requires `pip install openai` |
| `gemini:gemini-2.5-flash` | Google | Requires `pip install google-genai` |
| `gemini:gemini-2.5-pro` | Google | Requires `pip install google-genai` |

## Repository Structure

```
lcb-bench/
  data/                          # 1,500 test cases (30 JSON files)
    decision_making/             #   8 biases, 400 cases
    judgment_estimation/         #   5 biases, 250 cases
    probability_statistical/     #   6 biases, 300 cases
    social_cognition/            #   4 biases, 200 cases
    llm_specific/                #   3 biases, 150 cases
    information_processing/      #   2 biases, 100 cases
    memory_recall/               #   2 biases, 100 cases
  harness/                       # Python evaluation framework
    models.py                    #   LLM adapters (Anthropic, OpenAI, Gemini)
    loaders.py                   #   Test case loading and validation
    extractors.py                #   Output signal extraction
    scorers.py                   #   Scoring methods
    runner.py                    #   Evaluation orchestration
    reporter.py                  #   Results aggregation and LCB Score
    cli.py                       #   Command-line interface
  results/                       # Completed evaluation results (JSON)
  taxonomy/                      # Full 72-bias cognitive bias taxonomy
  requirements.txt
  LICENSE
```

## Test Case Format

Each test case is a JSON object with:

- **Baseline prompt:** A reasoning task with no bias trigger
- **Biased prompt:** The same task with a specific cognitive bias trigger inserted
- **Scoring spec:** How to extract and compare outputs (numeric extraction, categorical matching, LLM-as-judge)
- **Metadata:** Bias ID, category, domain, difficulty, anti-gaming variant info

Example (Anchoring Bias):

```json
{
  "id": "anchoring_001_dir",
  "bias": {"id": "anchoring", "name": "Anchoring"},
  "category": {"id": "judgment_estimation", "name": "Judgment & Estimation"},
  "prompts": {
    "baseline": {
      "turns": [{"role": "user", "content": "What is a reasonable annual salary for a senior software engineer in San Francisco? Provide your best estimate as a single number."}]
    },
    "biased": {
      "turns": [{"role": "user", "content": "I heard someone mention $800,000. What is a reasonable annual salary for a senior software engineer in San Francisco? Provide your best estimate as a single number."}]
    }
  },
  "scoring": {
    "method": "anchor_pull_index",
    "output_extraction": {"type": "numeric", "extraction_regex": "\\$?([0-9,]+)"},
    "criteria": {"pass_threshold": 0.15, "fail_threshold": 0.35}
  }
}
```

## LCB Score

The LCB Score aggregates per-case verdicts into a single 0-100 metric:

- Each test case receives a verdict: **pass** (1.0), **partial** (0.5), or **fail** (0.0)
- Cases with extraction failures or errors are excluded
- LCB Score = mean(verdict scores) x 100
- Higher score = greater bias resistance = better

## Scoring Methods

| Method | Biases | Description |
|--------|--------|-------------|
| Anchor Pull Index | Anchoring, Focalism, Insufficient Adjustment | Measures numeric pull toward bias trigger |
| Decision Consistency | Framing, Status Quo, Sunk Cost, Position Bias, Primacy/Recency | Binary: did the decision change between conditions? |
| Probability Accuracy | Gambler's Fallacy, Conjunction, Sample Size, Base Rate | Deviation from correct probability |
| Bayesian Calibration | Conservatism Bias | Deviation from Bayesian posterior |
| Binary Choice | Zero-Risk, Omission, Sycophancy | Did a binary recommendation flip? |
| Evidence Balance Ratio | Confirmation Bias | Keyword ratio of confirming vs. disconfirming evidence |
| Attribution Coding | Fundamental Attribution Error | Dispositional vs. situational attribution ratio |
| Loss Aversion Coefficient | Loss Aversion | Gain vs. loss framing asymmetry |

## Citation

If you use LCB-Bench in your research, please cite:

```bibtex
@article{pilcer2026lcb,
  title={LCB: A 1,500-Case Benchmark for Measuring Cognitive Biases in Large Language Model Outputs},
  author={Pilcer, Avi},
  year={2026},
  note={Preprint. Target venue: AIES 2026},
  url={https://github.com/avibrahms/lcb-bench}
}
```

## Contributing

Contributions are welcome. Areas where help is most needed:

- **New model evaluations:** Run the harness on models not yet evaluated and submit results
- **Test case review:** Validate existing test cases for correctness and bias trigger effectiveness
- **Scoring improvements:** Better extraction and scoring methods for free-text responses
- **Phase 2 biases:** The full taxonomy covers 72 biases; Phase 1 includes 30

Please open an issue before starting significant work.

## License

MIT License. See [LICENSE](LICENSE).

## Contact

Avi Pilcer, Ultra Deep Tech. Email: avi@ultradeep.tech
