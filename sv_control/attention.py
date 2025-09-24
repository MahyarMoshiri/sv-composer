"""Attention peak extraction from schema lexicon weights."""
from __future__ import annotations

from pydantic import BaseModel

from .lexicon import match_lemmas


class AttentionPeak(BaseModel):
    token: str
    w: float


def attention_weights(text: str, lang: str = "en", top_k: int = 5) -> list[AttentionPeak]:
    """Return the top weighted schema matches for the supplied text."""

    if top_k <= 0:
        return []

    scores = match_lemmas(text, lang=lang)
    if not scores:
        return []

    peaks = [AttentionPeak(token=schema_id, w=float(weight)) for schema_id, weight in scores.items() if weight > 0.0]
    return peaks[:top_k]
