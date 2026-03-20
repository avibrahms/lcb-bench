"""Load and validate LCB test cases from JSON files."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


class TestCase:
    """Parsed, validated LCB test case."""

    def __init__(self, raw: dict[str, Any]):
        self.raw = raw
        self.id: str = raw["id"]
        self.version: str = raw["version"]
        self.bias_id: str = raw["bias"]["id"]
        self.bias_name: str = raw["bias"]["name"]
        self.category_id: str = raw["category"]["id"]
        self.category_name: str = raw["category"]["name"]
        self.modality: str = raw["modality"]
        self.measurement_mode: str = raw["measurement_mode"]
        self.domain: str = raw.get("domain", "general")
        self.difficulty: str = raw.get("difficulty", "standard")
        self.prompts: dict = raw["prompts"]
        self.scoring: dict = raw["scoring"]

    @property
    def baseline_turns(self) -> list[dict]:
        return self.prompts["baseline"]["turns"]

    @property
    def biased_turns(self) -> list[dict]:
        return self.prompts["biased"]["turns"]

    @property
    def scoring_method(self) -> str:
        return self.scoring["method"]

    @property
    def extraction_type(self) -> str:
        return self.scoring["output_extraction"]["type"]

    @property
    def extraction_prompt(self) -> str | None:
        return self.scoring["output_extraction"].get("extraction_prompt")

    @property
    def extraction_regex(self) -> str | None:
        return self.scoring["output_extraction"].get("extraction_regex")

    @property
    def criteria(self) -> dict:
        return self.scoring["criteria"]

    def __repr__(self) -> str:
        return f"TestCase({self.id}, bias={self.bias_name}, method={self.scoring_method})"


def load_test_cases(path: str | Path) -> list[TestCase]:
    """Load test cases from a JSON file (schema: {test_cases: [...]}) or directory of such files."""
    path = Path(path)
    raw_cases: list[dict] = []

    if path.is_dir():
        for f in sorted(path.glob("**/*.json")):
            raw_cases.extend(_load_file(f))
    elif path.suffix == ".json":
        raw_cases.extend(_load_file(path))
    else:
        raise ValueError(f"Expected .json file or directory, got: {path}")

    return [TestCase(rc) for rc in raw_cases]


def _load_file(path: Path) -> list[dict]:
    with open(path) as f:
        data = json.load(f)

    # Support both {test_cases: [...]} wrapper and bare array
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "test_cases" in data:
        return data["test_cases"]
    return []
