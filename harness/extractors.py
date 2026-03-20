"""
Extract measurable signals from LLM free-text outputs.

Each extractor takes the raw model response and returns a typed value
suitable for the scoring layer.
"""
from __future__ import annotations

import re
from typing import Any

from .models import ModelAdapter


def extract(
    response: str,
    extraction_type: str,
    *,
    extraction_prompt: str | None = None,
    extraction_regex: str | None = None,
    valid_range: dict | None = None,
    categories: list[str] | None = None,
    judge: ModelAdapter | None = None,
) -> Any:
    """
    Dispatch to the right extractor based on extraction_type.

    Returns:
        float | str | bool | None  — None means extraction failed.
    """
    result = None
    match extraction_type:
        case "numeric":
            result = _extract_numeric(response, extraction_regex, valid_range)
        case "probability":
            result = _extract_probability(response, extraction_regex)
        case "binary_decision":
            result = _extract_binary(response, categories)
        case "categorical":
            result = _extract_categorical(response, categories or [])
        case "likert_scale":
            result = _extract_likert(response, extraction_regex)
        case "free_text_coded":
            result = _extract_free_text_coded(response, extraction_prompt, categories, judge)
        case "forced_choice":
            result = _extract_categorical(response, categories or [])
        case "ranking":
            result = _extract_ranking(response, categories or [])

    # Universal judge fallback: if keyword extraction failed and a judge is available,
    # ask the judge to classify the response into one of the categories.
    if result is None and judge is not None and categories:
        result = _extract_free_text_coded(response, extraction_prompt, categories, judge)

    return result


# ── Numeric ──────────────────────────────────────────────────────────────────

def _extract_numeric(
    text: str,
    regex: str | None,
    valid_range: dict | None,
) -> float | None:
    """Extract a single number from text."""
    if regex:
        m = re.search(regex, text.replace(",", ""))
        if m:
            try:
                val = float(m.group(1).replace(",", ""))
                return _clamp(val, valid_range)
            except (ValueError, IndexError):
                pass

    # Fallback: find all numbers, return last (often the final answer)
    nums = re.findall(r"-?\d+(?:\.\d+)?", text.replace(",", ""))
    if nums:
        val = float(nums[-1])
        return _clamp(val, valid_range)
    return None


def _clamp(val: float, valid_range: dict | None) -> float | None:
    if valid_range:
        lo, hi = valid_range.get("min", float("-inf")), valid_range.get("max", float("inf"))
        if not (lo <= val <= hi):
            return None
    return val


# ── Probability ───────────────────────────────────────────────────────────────

def _extract_probability(text: str, regex: str | None) -> float | None:
    """Extract a probability (0-1 or 0-100%) from text."""
    if regex:
        m = re.search(regex, text)
        if m:
            try:
                raw = float(m.group(1))
                return raw / 100.0 if raw > 1.0 else raw
            except (ValueError, IndexError):
                pass

    # Find percentages first
    pct = re.findall(r"(\d+(?:\.\d+)?)\s*%", text)
    if pct:
        return float(pct[-1]) / 100.0

    # Then decimals between 0-1
    nums = re.findall(r"0\.\d+", text)
    if nums:
        return float(nums[-1])

    return None


# ── Binary ────────────────────────────────────────────────────────────────────

def _extract_binary(text: str, categories: list[str] | None) -> bool | str | None:
    """Extract a yes/no or binary choice."""
    lower = text.lower()
    if categories:
        for cat in categories:
            if cat.lower() in lower:
                return cat
        return None

    # Default yes/no detection
    if re.search(r"\byes\b|\baccept\b|\bagree\b|\bproceed\b", lower):
        return True
    if re.search(r"\bno\b|\breject\b|\bdisagree\b|\bstop\b", lower):
        return False
    return None


# ── Categorical ───────────────────────────────────────────────────────────────

def _extract_categorical(text: str, categories: list[str]) -> str | None:
    """Extract which category from a list was chosen."""
    lower = text.lower()
    # Exact match first
    for cat in categories:
        if cat.lower() in lower:
            return cat
    # Sub-word match: split underscore-coded categories (e.g. "recommend_trial" → "trial")
    # Only use sub-words that are UNIQUE to one category (discriminating).
    # "response" in both "biased_response" and "unbiased_response" is useless.
    all_parts: dict[str, list[str]] = {}
    for cat in categories:
        parts = [p.lower() for p in re.split(r"[_\-]", cat) if len(p) > 3]
        all_parts[cat] = parts
    # Count how many categories share each sub-word
    part_counts: dict[str, int] = {}
    for parts in all_parts.values():
        for p in parts:
            part_counts[p] = part_counts.get(p, 0) + 1
    # Only match on discriminating sub-words (unique to one category)
    best = None
    best_pos = -1
    for cat, parts in all_parts.items():
        for part in parts:
            if part_counts.get(part, 0) > 1:
                continue  # appears in multiple categories, not discriminating
            idx = lower.rfind(part)
            if idx > best_pos:
                best_pos = idx
                best = cat
    if best is not None:
        return best
    return None


# ── Likert ────────────────────────────────────────────────────────────────────

def _extract_likert(text: str, regex: str | None) -> float | None:
    """Extract a Likert scale value (1-5, 1-7, etc.)."""
    if regex:
        m = re.search(regex, text)
        if m:
            try:
                return float(m.group(1))
            except (ValueError, IndexError):
                pass

    nums = re.findall(r"\b([1-9])\b", text)
    if nums:
        return float(nums[-1])
    return None


# ── Free-text coded (LLM judge) ───────────────────────────────────────────────

def _extract_free_text_coded(
    response: str,
    extraction_prompt: str | None,
    categories: list[str] | None,
    judge: ModelAdapter | None,
) -> str | None:
    """
    Use an LLM judge to extract a coded value from a free-text response.
    Falls back to keyword matching if no judge is available.
    """
    if judge is None:
        # No judge available: fall back to keyword matching
        if categories:
            return _extract_categorical(response, categories)
        return None

    # Auto-generate extraction prompt from categories if none provided
    if not extraction_prompt and categories:
        cats_formatted = "\n".join(f"- {cat}" for cat in categories)
        extraction_prompt = (
            f"Classify the following model response into exactly one of these categories:\n"
            f"{cats_formatted}\n\n"
            f"Reply with ONLY the category label exactly as written above. "
            f"No explanation, no quotes, no extra text."
        )

    if not extraction_prompt:
        return None

    prompt = f"{extraction_prompt}\n\nModel response to analyze:\n{response}"
    try:
        result = judge.complete(
            [{"role": "user", "content": prompt}],
            max_tokens=64,
        ).strip()
        # Validate: judge must return one of the valid categories
        if categories:
            # Exact match
            for cat in categories:
                if cat.lower() == result.lower():
                    return cat
            # Substring match (judge may add extra words)
            for cat in categories:
                if cat.lower() in result.lower():
                    return cat
        return result
    except Exception:
        if categories:
            return _extract_categorical(response, categories)
        return None


# ── Ranking ───────────────────────────────────────────────────────────────────

def _extract_ranking(text: str, categories: list[str]) -> list[str] | None:
    """Extract a ranked ordering of categories from text."""
    found = []
    positions = {}
    for cat in categories:
        idx = text.lower().find(cat.lower())
        if idx != -1:
            positions[cat] = idx
    if positions:
        ranked = sorted(positions, key=lambda c: positions[c])
        return ranked
    return None
