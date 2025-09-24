"""Local LLM harness abstractions and lightweight test doubles."""
from __future__ import annotations

import importlib
import logging
import os
from typing import Optional, Protocol, runtime_checkable


LLM_SPEC_ENV = "SV_LLM_IMPL"
LLM_FACTORY_ENV = "SV_LLM_FACTORY"
DEFAULT_FACTORY_NAME = "create_llm"
DEFAULT_LLM_NAME = "openai"
DEFAULT_FALLBACK_NAME = "echo"
DEFAULT_ENV = "SV_LLM_DEFAULT"
OFFLINE_ENV = "SV_OFFLINE"


logger = logging.getLogger(__name__)


@runtime_checkable
class LLM(Protocol):
    """Minimal interface required by the generation controller."""

    def generate(self, prompt: str, max_new_tokens: int = 200) -> str:  # pragma: no cover - protocol
        """Return model text for the given prompt."""


class EchoLLM:
    """Deterministic harness used in tests and offline smoke runs."""

    def generate(self, prompt: str, max_new_tokens: int = 200) -> str:
        """Echo the first non-empty line of the prompt within the token budget."""

        lines = [line.strip() for line in prompt.splitlines() if line.strip()]
        if not lines:
            return ""
        head = lines[0]
        if max_new_tokens and max_new_tokens > 0:
            return head[:max_new_tokens].strip()
        return head


def _load_custom_provider(module_path: str, name: str) -> LLM:
    module = importlib.import_module(module_path)
    factory_name = os.getenv(LLM_FACTORY_ENV, DEFAULT_FACTORY_NAME)
    factory = getattr(module, factory_name, None)
    if factory is None:
        raise ImportError(
            f"Factory '{factory_name}' not found in '{module_path}'. Adjust {LLM_FACTORY_ENV}."
        )
    harness = factory(name=name)
    if not isinstance(harness, LLM) and not hasattr(harness, "generate"):
        raise TypeError(
            f"Custom harness '{name}' from '{module_path}' does not expose a generate() method."
        )
    return harness  # type: ignore[return-value]


class _FallbackOnErrorLLM:
    """Wrapper that downshifts to a fallback harness after the first failure."""

    def __init__(self, primary: LLM, fallback: LLM) -> None:
        self._primary: Optional[LLM] = primary
        self._fallback: LLM = fallback
        self._using_primary = True

    def generate(self, prompt: str, max_new_tokens: int = 200) -> str:
        if self._using_primary and self._primary is not None:
            try:
                return self._primary.generate(prompt, max_new_tokens=max_new_tokens)
            except Exception as exc:  # noqa: BLE001 - fallback guard
                logger.warning("Primary LLM failed; switching to EchoLLM: %s", exc)
                self._using_primary = False
                self._primary = None
        return self._fallback.generate(prompt, max_new_tokens=max_new_tokens)


def _load_openai_provider(name: str) -> LLM:
    from sv_llm.providers import openai as openai_provider

    return openai_provider.create_llm(name=name)


def get_llm(name: str | None = None) -> LLM:
    offline = os.getenv(OFFLINE_ENV, "").strip() == "1"
    if offline:
        logger.info("SV_OFFLINE=1 → using EchoLLM")
        return EchoLLM()

    requested = (name or os.getenv(DEFAULT_ENV, DEFAULT_LLM_NAME)).strip().lower()
    if requested in {"", DEFAULT_FALLBACK_NAME}:
        return EchoLLM()

    provider_module = os.getenv(LLM_SPEC_ENV)
    if provider_module:
        try:
            return _load_custom_provider(provider_module, requested)
        except Exception as exc:  # noqa: BLE001 - surfaced as warning/fallback
            logger.warning(
                "Custom LLM provider '%s' failed; falling back to EchoLLM: %s",
                provider_module,
                exc,
            )
            return EchoLLM()

    if requested == DEFAULT_LLM_NAME:
        try:
            primary = _load_openai_provider(requested)
        except Exception as exc:  # noqa: BLE001 - fallback to echo
            logger.warning("OpenAI provider unavailable; using EchoLLM: %s", exc)
            return EchoLLM()
        return _FallbackOnErrorLLM(primary, EchoLLM())

    raise ValueError(
        f"Unknown LLM harness '{requested}'. Set {LLM_SPEC_ENV} for custom providers or use 'echo'."
    )


def default_llm_name() -> str:
    """Return the configured default harness name without instantiating it."""

    if os.getenv(OFFLINE_ENV, "").strip() == "1":
        return DEFAULT_FALLBACK_NAME

    requested = os.getenv(DEFAULT_ENV, DEFAULT_LLM_NAME).strip().lower()
    if requested in {"", DEFAULT_FALLBACK_NAME}:
        return DEFAULT_FALLBACK_NAME

    if os.getenv(LLM_SPEC_ENV):
        return requested

    if requested == DEFAULT_LLM_NAME:
        api_key_present = bool(os.getenv("OPENAI_API_KEY", "").strip())
        has_sdk = importlib.util.find_spec("openai") is not None  # type: ignore[attr-defined]
        if api_key_present and has_sdk:
            return DEFAULT_LLM_NAME
        return DEFAULT_FALLBACK_NAME

    return requested


def load_llm(name: str) -> LLM:
    """Backwards-compatible alias for get_llm()."""

    return get_llm(name or None)


__all__ = ["LLM", "EchoLLM", "default_llm_name", "get_llm", "load_llm"]
