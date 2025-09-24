"""Built-in OpenAI provider for the SV LLM harness."""
from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Optional


try:  # pragma: no cover - import guarded for offline/test environments
    from openai import OpenAI
except Exception:  # noqa: BLE001 - surfaced at runtime
    OpenAI = None  # type: ignore[assignment]


class OpenAILLM:
    """Minimal Chat Completions wrapper satisfying the LLM protocol."""

    def __init__(self, *, model: str, temperature: float, timeout: int) -> None:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key or OpenAI is None:
            raise RuntimeError("OpenAI client unavailable (missing SDK or OPENAI_API_KEY).")

        base_url = os.getenv("OPENAI_BASE_URL", "").strip() or None
        timeout = max(1, timeout)
        # The v1 SDK picks up the API key from the environment by default; pass explicit
        # values for clarity and deterministic behaviour.
        self._client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        self.model = model
        self.temperature = temperature

    def _max_tokens(self, value: Optional[int]) -> int:
        if value is None:
            return 200
        try:
            tokens = int(value)
        except (TypeError, ValueError):
            tokens = 200
        return max(1, tokens)

    def generate(self, prompt: str, max_new_tokens: int = 200) -> str:
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=self._max_tokens(max_new_tokens),
            top_p=1.0,
        )
        choice = response.choices[0]
        return (choice.message.content or "").strip()


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def create_llm(*, name: str) -> OpenAILLM:  # pragma: no cover - integration glue
    model = os.getenv("SV_OPENAI_MODEL", "gpt-5").strip() or "gpt-5"
    temperature = _env_float("SV_OPENAI_TEMPERATURE", 0.7)
    timeout = _env_int("SV_OPENAI_TIMEOUT", 20)
    return OpenAILLM(model=model, temperature=temperature, timeout=timeout)


__all__ = ["create_llm", "OpenAILLM"]

