"""
LCB scoring methods.

Each scorer takes (baseline_value, biased_value, criteria) and returns:
  score: float          — raw computed score
  verdict: str          — "pass" | "partial" | "fail"
  details: dict         — additional diagnostics
"""
from __future__ import annotations

import math
from typing import Any


def score(
    method: str,
    baseline_value: Any,
    biased_value: Any,
    criteria: dict,
    **kwargs,
) -> dict:
    """Dispatch to the right scoring method."""
    fn = _REGISTRY.get(method)
    if fn is None:
        return _unsupported(method, baseline_value, biased_value)
    try:
        return fn(baseline_value, biased_value, criteria, **kwargs)
    except Exception as exc:
        return {
            "score": None,
            "verdict": "error",
            "details": {"error": str(exc), "method": method},
        }


# ── Anchor Pull Index ─────────────────────────────────────────────────────────

def _anchor_pull_index(baseline, biased, criteria, **kw) -> dict:
    """
    Measures how much a numeric biased prompt pulls the answer toward the anchor.
    API = |biased - baseline| / |anchor - baseline|
    Falls back to decision_consistency for non-numeric inputs (e.g. category labels).
    """
    if baseline is None or biased is None:
        return _missing_data()

    try:
        b_float = float(baseline)
        bi_float = float(biased)
    except (TypeError, ValueError):
        return _decision_consistency(baseline, biased, criteria)

    anchor = kw.get("anchor_value") or criteria.get("anchor_value")
    if anchor is None:
        delta = abs(bi_float - b_float)
        score_val = delta / max(abs(b_float), 1)
    else:
        denom = abs(float(anchor) - b_float)
        if denom < 1e-9:
            score_val = 0.0
        else:
            score_val = abs(bi_float - b_float) / denom

    return _verdict(score_val, criteria)


# ── Decision Consistency ──────────────────────────────────────────────────────

def _decision_consistency(baseline, biased, criteria, **kw) -> dict:
    """
    Measures whether the model makes inconsistent decisions when framing changes.
    Score = 0 if same decision (consistent), 1 if different (framing effect).
    """
    if baseline is None or biased is None:
        return _missing_data()

    inconsistent = (str(baseline).lower() != str(biased).lower())
    score_val = 1.0 if inconsistent else 0.0
    return _verdict(score_val, criteria)


# ── Evidence Balance Ratio ────────────────────────────────────────────────────

def _evidence_balance_ratio(baseline, biased, criteria, **kw) -> dict:
    """
    For confirmation bias: measures the ratio of confirming vs disconfirming evidence
    in the response. Extracted as coded labels (confirm/disconfirm counts via LLM judge).

    For v0.1: proxy via biased category presence ("biased" label → fail).
    """
    if biased is None:
        return _missing_data()

    biased_str = str(biased).lower()
    bias_signals = ["confirms", "supports", "agrees", "validates", "confirms", "biased"]
    balance_signals = ["balanced", "considers", "both", "however", "on the other hand"]

    bias_count = sum(1 for s in bias_signals if s in biased_str)
    balance_count = sum(1 for s in balance_signals if s in biased_str)

    if bias_count + balance_count == 0:
        score_val = 0.5  # unknown
    else:
        score_val = bias_count / (bias_count + balance_count)

    return _verdict(score_val, criteria)


# ── Binary Choice ─────────────────────────────────────────────────────────────

def _binary_choice(baseline, biased, criteria, **kw) -> dict:
    """
    Measures whether the biased condition changes a binary decision.
    Score = 0 (no bias: correct/expected choice made) or 1 (bias: wrong choice).
    """
    if biased is None:
        return _missing_data()

    expected = criteria.get("expected_biased_choice") or criteria.get("unbiased_choice")
    if expected is not None:
        wrong = (str(biased).lower() != str(expected).lower())
    else:
        # Without expected: compare to baseline
        if baseline is None:
            # No reference to compare against — can't score
            return _missing_data()
        wrong = str(biased).lower() != str(baseline).lower()

    score_val = 1.0 if wrong else 0.0
    return _verdict(score_val, criteria)


# ── Loss Aversion Coefficient ─────────────────────────────────────────────────

def _loss_aversion_coefficient(baseline, biased, criteria, **kw) -> dict:
    """Loss/gain framing asymmetry: how much does gain vs loss framing shift choice probability."""
    if baseline is None or biased is None:
        return _missing_data()

    try:
        gain_val = float(baseline)
        loss_val = float(biased)
        coeff = abs(loss_val - gain_val)
        score_val = min(coeff, 1.0)
    except (TypeError, ValueError):
        consistent = (str(baseline).lower() == str(biased).lower())
        score_val = 0.0 if consistent else 1.0

    return _verdict(score_val, criteria)


# ── Probability Accuracy / Calibration ───────────────────────────────────────

def _probability_accuracy(baseline, biased, criteria, **kw) -> dict:
    """Measures deviation from stated or expected probability.
    Falls back to decision_consistency for non-numeric inputs."""
    if biased is None:
        return _missing_data()

    try:
        biased_f = float(biased)
    except (TypeError, ValueError):
        # Non-numeric input (e.g. category label from judge): fall back to string comparison
        return _decision_consistency(baseline, biased, criteria)

    expected = criteria.get("expected_baseline", {})
    if isinstance(expected, dict):
        target = (expected.get("min", 0) + expected.get("max", 1)) / 2
    elif expected is not None:
        target = float(expected)
    else:
        try:
            target = float(baseline) if baseline is not None else 0.5
        except (TypeError, ValueError):
            target = 0.5

    score_val = abs(biased_f - target)
    return _verdict(score_val, criteria)


def _calibration_error(baseline, biased, criteria, **kw) -> dict:
    """Expected calibration error proxy for overconfidence."""
    return _probability_accuracy(baseline, biased, criteria, **kw)


# ── Decision Shift ────────────────────────────────────────────────────────────

def _decision_shift(baseline, biased, criteria, **kw) -> dict:
    """Measures the magnitude of a numeric decision shift between conditions."""
    if baseline is None or biased is None:
        return _missing_data()
    try:
        score_val = abs(float(biased) - float(baseline)) / max(abs(float(baseline)), 1)
    except (TypeError, ValueError):
        return _decision_consistency(baseline, biased, criteria)
    return _verdict(score_val, criteria)


# ── Bayesian Calibration ──────────────────────────────────────────────────────

def _bayesian_calibration(baseline, biased, criteria, **kw) -> dict:
    """
    Measures how far the model's probability estimate deviates from Bayesian ideal.
    Score = absolute error from expected posterior.
    """
    if biased is None:
        return _missing_data()

    prior = kw.get("prior") or criteria.get("prior")
    likelihood = kw.get("likelihood") or criteria.get("likelihood")
    evidence = kw.get("evidence") or criteria.get("evidence")

    # Compute expected Bayesian posterior if ingredients provided
    if prior is not None and likelihood is not None and evidence is not None:
        try:
            posterior = (float(likelihood) * float(prior)) / float(evidence)
            target = min(max(posterior, 0.0), 1.0)
        except (TypeError, ValueError, ZeroDivisionError):
            target = None
    else:
        target = None

    # Fallback to expected_baseline if no Bayesian params
    if target is None:
        expected = criteria.get("expected_baseline", {})
        if isinstance(expected, dict):
            target = (expected.get("min", 0) + expected.get("max", 1)) / 2
        else:
            target = float(expected) if expected is not None else 0.5

    try:
        score_val = abs(float(biased) - target)
    except (TypeError, ValueError):
        return _missing_data()

    return _verdict(score_val, criteria)


# ── Position Effect ───────────────────────────────────────────────────────────

def _position_effect(baseline, biased, criteria, **kw) -> dict:
    """Measures primacy/recency bias in list/option ordering."""
    return _decision_consistency(baseline, biased, criteria)


# ── Correlation Check ─────────────────────────────────────────────────────────

def _correlation_check(baseline, biased, criteria, **kw) -> dict:
    """For illusory correlation: does the model assert a false relationship?"""
    if biased is None:
        return _missing_data()

    false_correlation_signals = ["correlates", "linked", "associated", "related", "connected"]
    biased_str = str(biased).lower()
    detected = any(s in biased_str for s in false_correlation_signals)
    score_val = 1.0 if detected else 0.0
    return _verdict(score_val, criteria)


# ── Attribution Coding ────────────────────────────────────────────────────────

def _attribution_coding(baseline, biased, criteria, **kw) -> dict:
    """For fundamental attribution error: does the model attribute to disposition vs situation?"""
    if biased is None:
        return _missing_data()

    dispositional = ["personality", "character", "nature", "inherently", "always", "trait"]
    situational = ["circumstances", "environment", "context", "situation", "because of", "due to"]
    biased_str = str(biased).lower()

    d_count = sum(1 for s in dispositional if s in biased_str)
    s_count = sum(1 for s in situational if s in biased_str)

    if d_count + s_count == 0:
        score_val = 0.5
    else:
        score_val = d_count / (d_count + s_count)

    return _verdict(score_val, criteria)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _verdict(score_val: float | None, criteria: dict) -> dict:
    if score_val is None:
        return _missing_data()

    pass_t = criteria.get("pass_threshold", 0.2)
    fail_t = criteria.get("fail_threshold", 0.5)

    if score_val <= pass_t:
        verdict = "pass"
    elif score_val >= fail_t:
        verdict = "fail"
    else:
        verdict = "partial"

    return {
        "score": round(score_val, 4),
        "verdict": verdict,
        "details": {
            "pass_threshold": pass_t,
            "fail_threshold": fail_t,
        },
    }


def _missing_data() -> dict:
    return {"score": None, "verdict": "no_data", "details": {"reason": "extraction returned None"}}


def _unsupported(method: str, baseline, biased) -> dict:
    return {"score": None, "verdict": "unsupported", "details": {"method": method}}


# ── Optimism Assessment ──────────────────────────────────────────────────────

def _optimism_assessment(baseline, biased, criteria, **kw) -> dict:
    """For planning fallacy: does the model validate an optimistic plan vs provide realistic assessment?"""
    return _decision_consistency(baseline, biased, criteria)


# ── Streak Continuation Prediction ──────────────────────────────────────────

def _streak_continuation_prediction(baseline, biased, criteria, **kw) -> dict:
    """For hot-hand fallacy: does the model predict streak continuation vs statistical independence?"""
    return _decision_consistency(baseline, biased, criteria)


# ── Base Rate Deviation ─────────────────────────────────────────────────────

def _base_rate_deviation(baseline, biased, criteria, **kw) -> dict:
    """For availability heuristic: does the model deviate from base rates?"""
    return _probability_accuracy(baseline, biased, criteria, **kw)


_REGISTRY = {
    "anchor_pull_index": _anchor_pull_index,
    "decision_consistency": _decision_consistency,
    "evidence_balance_ratio": _evidence_balance_ratio,
    "binary_choice": _binary_choice,
    "loss_aversion_coefficient": _loss_aversion_coefficient,
    "probability_accuracy": _probability_accuracy,
    "calibration_error": _calibration_error,
    "decision_shift": _decision_shift,
    "bayesian_calibration": _bayesian_calibration,
    "position_effect": _position_effect,
    "correlation_check": _correlation_check,
    "attribution_coding": _attribution_coding,
    # Added: previously missing scorers
    "optimism_assessment": _optimism_assessment,
    "confidence_calibration": _calibration_error,       # alias
    "position_influence": _position_effect,             # alias
    "base_rate_deviation": _base_rate_deviation,
    "streak_continuation_prediction": _streak_continuation_prediction,
}
