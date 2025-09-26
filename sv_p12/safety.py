"""Safety utilities for constructing guarded prompts."""
from __future__ import annotations

from collections import OrderedDict
from typing import Iterable, List, Tuple

GLOBAL_BANS = OrderedDict(
    (
        ("violence", "no-violence"),
        ("gore", "no-violence"),
        ("hate", "no-hate"),
        ("explicit sex", "no-explicit"),
        ("pii", "no-PII"),
    )
)


def compile_negative_prompt(tokens: Iterable[str]) -> Tuple[str, List[str]]:
    """Merge per-beat bans with global guardrails."""

    ordered = OrderedDict()
    for token in tokens:
        normalized = str(token).strip().lower()
        if normalized:
            ordered[normalized] = None

    for ban in GLOBAL_BANS:
        ordered.setdefault(ban, None)

    negative_prompt = ", ".join(ordered.keys())
    tags = sorted(set(GLOBAL_BANS.values()))
    return negative_prompt, tags


__all__ = ["GLOBAL_BANS", "compile_negative_prompt"]
