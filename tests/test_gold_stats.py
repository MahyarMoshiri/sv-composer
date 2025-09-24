from __future__ import annotations

from pathlib import Path

import pytest

from sv_sdk.gold_loader import load_gold_jsonl
from sv_sdk.gold_stats import compute_gold_stats

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "gold_small.jsonl"


def test_gold_stats_fixture() -> None:
    gold = load_gold_jsonl(FIXTURE)
    stats = compute_gold_stats(gold)

    assert stats["count"] == 2
    assert stats["by_lang"] == {"en": 1, "fa": 1}
    assert stats["by_frame"] == {"journey": 1, "threshold_crossing": 1}
    assert stats["by_schema"] == {"boundary": 1, "container": 1, "path": 1}
    assert stats["by_metaphor"] == {"life_is_travel": 1, "raw_cooked": 1}
    assert stats["explosion_beats"] == {3: 1, 4: 1}
    assert stats["attention"]["count"] == 4
    assert stats["attention"]["avg_weight"] == pytest.approx(0.7)
    assert stats["metaphor_poles"] == {
        "with_pole": 1,
        "total": 2,
        "percent_with_pole": pytest.approx(50.0),
    }
