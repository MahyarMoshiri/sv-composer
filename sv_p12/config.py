"""Configuration helpers for the P12 single-prompt film planning module."""
from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Optional

try:  # pragma: no cover - optional dependency
    from openai import OpenAI
except Exception:  # noqa: BLE001 - import guard when SDK unavailable
    OpenAI = None  # type: ignore[assignment]


@dataclass
class P12Config:
    """Runtime configuration for P12 enrichment clients."""

    api_key: str
    model: str = "gpt-4o-mini"
    base_url: Optional[str] = None
    temperature: float = 0.35

    @classmethod
    def from_env(cls) -> "P12Config":
        """Construct from environment variables.

        Uses OPENAI_P12_* keys with sensible defaults.
        """
        api_key = os.getenv("OPENAI_P12_API_KEY", "").strip()
        model = (os.getenv("OPENAI_P12_MODEL", "gpt-4o-mini") or "gpt-4o-mini").strip()
        base_url = os.getenv("OPENAI_P12_BASE_URL") or None
        try:
            temperature = float(os.getenv("OPENAI_P12_TEMPERATURE", "0.35"))
        except ValueError:
            temperature = 0.35
        return cls(api_key=api_key, model=model, base_url=base_url, temperature=temperature)


def _env(name: str) -> str:
    value = os.getenv(name)
    return value.strip() if isinstance(value, str) else ""


def load_p12_config() -> Optional[P12Config]:
    """Load configuration from environment, preferring P12 overrides."""

    api_key = _env("OPENAI_P12_API_KEY") or _env("OPENAI_API_KEY")
    if not api_key:
        return None

    model = _env("OPENAI_P12_MODEL") or _env("OPENAI_MODEL") or "gpt-4o-mini"
    base_url = _env("OPENAI_P12_BASE_URL") or _env("OPENAI_BASE_URL") or None

    def _float_env(primary: str, fallback: str, default: float) -> float:
        raw = _env(primary) or _env(fallback)
        if not raw:
            return default
        try:
            return max(0.0, float(raw))
        except ValueError:
            return default

    temperature = _float_env("OPENAI_P12_TEMPERATURE", "OPENAI_TEMPERATURE", 0.35)

    cfg = P12Config(api_key=api_key, model=model, base_url=base_url, temperature=temperature)
    return cfg


def get_p12_openai_client(cfg: Optional[P12Config] = None, *, timeout: int = 10) -> Optional["OpenAI"]:
    """Instantiate an OpenAI client using P12 configuration when available."""

    if cfg is None:
        cfg = load_p12_config()
    if cfg is None or OpenAI is None:
        return None

    kwargs = {"api_key": cfg.api_key, "timeout": max(1, timeout)}
    if cfg.base_url:
        kwargs["base_url"] = cfg.base_url
    return OpenAI(**kwargs)


__all__ = ["P12Config", "get_p12_openai_client", "load_p12_config"]
