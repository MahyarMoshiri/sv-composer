"""Aggregate statistics for the gold-labelled corpus."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict

from .models import GoldSet


def _sorted(counter: Counter[str]) -> Dict[str, int]:
    return dict(sorted(counter.items()))


def compute_gold_stats(gold: GoldSet) -> Dict[str, Any]:
    """Compute descriptive statistics for the gold corpus."""

    lang_counts: Counter[str] = Counter()
    frame_counts: Counter[str] = Counter()
    schema_counts: Counter[str] = Counter()
    metaphor_counts: Counter[str] = Counter()
    beat_counts: Counter[int] = Counter()

    attention_weights: list[float] = []
    total_metaphors = 0
    with_pole = 0

    for label in gold:
        lang_counts[label.lang] += 1

        if label.labels.frame is not None:
            frame_counts[label.labels.frame.id] += 1

        for schema in label.labels.schemas:
            schema_counts[schema.id] += 1

        for metaphor in label.labels.metaphors:
            metaphor_counts[metaphor.id] += 1
            total_metaphors += 1
            if metaphor.pole is not None:
                with_pole += 1

        if label.labels.explosion is not None:
            beat_counts[label.labels.explosion.beat] += 1

        for attention in label.labels.attention:
            attention_weights.append(float(attention.w))

    attention_avg = sum(attention_weights) / len(attention_weights) if attention_weights else 0.0
    pole_pct = (with_pole / total_metaphors * 100.0) if total_metaphors else 0.0

    return {
        "count": len(gold),
        "by_lang": _sorted(lang_counts),
        "by_frame": _sorted(frame_counts),
        "by_schema": _sorted(schema_counts),
        "by_metaphor": _sorted(metaphor_counts),
        "explosion_beats": dict(sorted(beat_counts.items())),
        "attention": {
            "avg_weight": attention_avg,
            "count": len(attention_weights),
        },
        "metaphor_poles": {
            "with_pole": with_pole,
            "total": total_metaphors,
            "percent_with_pole": pole_pct,
        },
    }
