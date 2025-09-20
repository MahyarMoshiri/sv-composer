"""Lexicon-based schema matching helpers."""
from __future__ import annotations

from collections import defaultdict
from typing import Dict

from sv_sdk.loader import load_schema_bank


def match_lemmas(text: str, lang: str = "en") -> Dict[str, float]:
    """Match lemmas in the given text against the schema lexicon."""

    tokens = {token for token in text.lower().split() if token}
    if not tokens:
        return {}

    bank = load_schema_bank()
    scores: Dict[str, float] = defaultdict(float)

    for schema in bank.schemas:
        lexicon = schema.lexicon.model_dump().get(lang, [])
        if not isinstance(lexicon, list):
            continue
        for lexeme_data in lexicon:
            lemma = str(lexeme_data.get("lemma", "")).lower()
            if lemma and lemma in tokens:
                weight = float(lexeme_data.get("w", 0.0))
                scores[schema.id] += weight

    sorted_scores = dict(sorted(scores.items(), key=lambda item: item[1], reverse=True))
    return sorted_scores
