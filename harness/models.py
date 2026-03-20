"""LLM model adapters for multi-provider support."""
from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

# Default model for evaluations — fast + cheap, good for bulk runs.
# Pin to a specific version to ensure reproducible results across runs.
DEFAULT_MODEL = "anthropic:claude-haiku-4-5-20251001"


class ModelAdapter(ABC):
    """Base class for LLM model adapters."""

    @abstractmethod
    def complete(self, messages: list[dict[str, str]], *, max_tokens: int = 1024) -> str:
        """Run a chat completion and return the text content."""
        ...

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Canonical model identifier (used in result records)."""
        ...


class AnthropicAdapter(ModelAdapter):
    """Adapter for Anthropic Claude models."""

    def __init__(self, model: str = "claude-haiku-4-5-20251001", api_key: str | None = None):
        import anthropic
        self._model = model
        self._client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    @property
    def model_id(self) -> str:
        return self._model

    def complete(self, messages: list[dict[str, str]], *, max_tokens: int = 1024) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=messages,
        )
        return response.content[0].text


class OpenAIAdapter(ModelAdapter):
    """Adapter for OpenAI-compatible APIs (OpenAI, local, etc.)."""

    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None, base_url: str | None = None):
        try:
            import openai
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")
        self._model = model
        self._client = openai.OpenAI(
            api_key=api_key or os.environ.get("OPENAI_API_KEY"),
            base_url=base_url,
        )

    @property
    def model_id(self) -> str:
        return self._model

    def complete(self, messages: list[dict[str, str]], *, max_tokens: int = 1024) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content


class GeminiAdapter(ModelAdapter):
    """Adapter for Google Gemini models via the google-genai SDK.

    Supports two auth modes:
    - api_key / GEMINI_API_KEY: Google AI Studio key (default)
    - service_account_json / GOOGLE_APPLICATION_CREDENTIALS: Vertex AI service account
    - Auto-discovers .gemini-sa.json in lcb-bench/ directory as fallback
    """

    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        api_key: str | None = None,
        service_account_json: str | None = None,
        project: str | None = None,
        location: str = "us-central1",
    ):
        try:
            from google import genai
        except ImportError:
            raise ImportError("google-genai package not installed. Run: pip install google-genai")

        sa_path = service_account_json or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        # Auto-discover service account from project config if not explicitly set
        if not sa_path:
            _cfg = Path(__file__).resolve().parent.parent / ".gemini-sa.json"
            if _cfg.is_file():
                sa_path = str(_cfg)
        key = api_key or os.environ.get("GEMINI_API_KEY")

        if sa_path:
            # Vertex AI path — service account credentials
            import json as _json
            with open(sa_path) as f:
                sa_info = _json.load(f)
            proj = project or sa_info.get("project_id") or os.environ.get("GOOGLE_CLOUD_PROJECT")
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = sa_path
            self._client = genai.Client(vertexai=True, project=proj, location=location)
        elif key:
            self._client = genai.Client(api_key=key)
        else:
            raise ValueError(
                "No Gemini auth provided. Set GEMINI_API_KEY or GOOGLE_APPLICATION_CREDENTIALS, "
                "or place a .gemini-sa.json service account file in the lcb-bench/ directory."
            )
        self._model = model
        self._thinking_unsupported = False  # Set True if model rejects thinking_budget=0

    @property
    def model_id(self) -> str:
        return self._model

    def complete(self, messages: list[dict[str, str]], *, max_tokens: int = 1024) -> str:
        from google.genai import types
        # Convert OpenAI-style messages to Gemini contents
        contents = []
        system_instruction = None
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            else:
                role = "user" if msg["role"] == "user" else "model"
                contents.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))
        # Disable thinking for eval workloads — thinking tokens consume output budget
        # and are unnecessary for structured bias measurement tasks.
        # Some models (e.g. gemini-2.5-pro) reject thinking_budget=0; we try with
        # thinking disabled first, then fall back to no thinking config.
        thinking_config = None
        if not self._thinking_unsupported:
            try:
                thinking_config = types.ThinkingConfig(thinking_budget=0)
            except AttributeError:
                pass  # Older SDK version without ThinkingConfig

        config = types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            system_instruction=system_instruction,
            **({"thinking_config": thinking_config} if thinking_config is not None else {}),
        )
        # Retry with exponential backoff for rate limits (429)
        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = self._client.models.generate_content(
                    model=self._model,
                    contents=contents,
                    config=config,
                )
                text = response.text
                if text is None:
                    finish = response.candidates[0].finish_reason if response.candidates else "unknown"
                    raise ValueError(f"Model returned None text (finish_reason={finish}). "
                                     "Try increasing max_tokens or check model response.")
                return text
            except Exception as e:
                err_str = str(e)
                # If model rejects thinking_budget=0, retry without thinking config
                if "thinking_budget" in err_str and not self._thinking_unsupported:
                    self._thinking_unsupported = True
                    config = types.GenerateContentConfig(
                        max_output_tokens=max_tokens,
                        system_instruction=system_instruction,
                    )
                    continue
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    wait = 2 ** attempt + 1  # 2, 3, 5, 9, 17 seconds
                    if attempt < max_retries - 1:
                        time.sleep(wait)
                        continue
                raise


class ClaudeCodeAdapter(ModelAdapter):
    """Adapter that uses the local Claude Code CLI as the model.

    Shells out to `claude -p` with CLAUDECODE unset to avoid nesting errors.
    Explicitly passes --model to guarantee the exact model used.
    Each call spawns a subprocess — slower than API but zero API cost.

    model_label: Used in result records (e.g. "claude-sonnet-4-6").
    cli_model: Passed to `claude -p --model <cli_model>` (e.g. "sonnet").
    """

    # Map model labels to CLI --model flags
    _CLI_MODEL_MAP = {
        "claude-sonnet-4-6": "sonnet",
        "claude-opus-4-6": "opus",
        "claude-haiku-4-5": "haiku",
    }

    def __init__(self, model_label: str = "claude-sonnet-4-6", cli_model: str | None = None):
        self._model_label = model_label
        self._cli_model = cli_model or self._CLI_MODEL_MAP.get(model_label, "sonnet")

    @property
    def model_id(self) -> str:
        return self._model_label

    def complete(self, messages: list[dict[str, str]], *, max_tokens: int = 1024) -> str:
        import subprocess

        # Build a single prompt from messages
        parts = []
        for msg in messages:
            if msg["role"] == "system":
                parts.append(f"[System instruction]: {msg['content']}")
            elif msg["role"] == "user":
                parts.append(msg["content"])
            elif msg["role"] == "assistant":
                parts.append(f"[Previous assistant response]: {msg['content']}")
        prompt = "\n\n".join(parts)

        # Run claude CLI with CLAUDECODE unset to allow subprocess invocation
        env = os.environ.copy()
        env.pop("CLAUDECODE", None)

        # Retry with backoff for transient failures
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = subprocess.run(
                    ["claude", "-p", prompt, "--output-format", "text", "--max-turns", "1",
                     "--model", self._cli_model],
                    capture_output=True,
                    text=True,
                    env=env,
                    timeout=180,
                )
                if result.returncode != 0:
                    raise RuntimeError(f"claude CLI failed (rc={result.returncode}): {result.stderr[:500]}")
                text = result.stdout.strip()
                if not text:
                    raise ValueError("claude CLI returned empty response")
                return text
            except subprocess.TimeoutExpired:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise RuntimeError("claude CLI timed out after 180s (3 retries exhausted)")
            except FileNotFoundError:
                raise RuntimeError("claude CLI not found. Install Claude Code: https://docs.anthropic.com/claude-code")
            except (RuntimeError, ValueError):
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise


def get_adapter(model_spec: str, **kwargs) -> ModelAdapter:
    """
    Create a model adapter from a model specification string.

    Spec format: "provider:model_id"
    Examples:
        "anthropic:claude-haiku-4-5-20251001"
        "anthropic:claude-sonnet-4-6"
        "openai:gpt-4o-mini"
        "openai:gpt-4o"
        "gemini:gemini-2.5-flash"
        "gemini:gemini-2.5-pro"

    For backwards-compat, bare model names are tried against known prefixes.
    """
    if ":" in model_spec:
        provider, model_id = model_spec.split(":", 1)
    else:
        # Infer provider from model name
        if model_spec.startswith("claude"):
            provider, model_id = "anthropic", model_spec
        elif model_spec.startswith("gpt") or model_spec.startswith("o1") or model_spec.startswith("o3"):
            provider, model_id = "openai", model_spec
        elif model_spec.startswith("gemini"):
            provider, model_id = "gemini", model_spec
        else:
            raise ValueError(f"Cannot infer provider for model: {model_spec}. Use 'provider:model_id' format.")

    if provider == "anthropic":
        return AnthropicAdapter(model=model_id, **kwargs)
    if provider == "openai":
        return OpenAIAdapter(model=model_id, **kwargs)
    if provider == "gemini":
        return GeminiAdapter(model=model_id, **kwargs)

    if provider == "claude-code":
        return ClaudeCodeAdapter(model_label=model_id or "claude-sonnet-4-6", **kwargs)

    raise ValueError(f"Unknown provider: {provider}. Supported: anthropic, openai, gemini, claude-code")
