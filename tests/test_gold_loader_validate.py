from __future__ import annotations

from pathlib import Path

import pytest

from sv_sdk.gold_loader import load_gold_jsonl
from sv_sdk.loader import load_beats_config, load_frame_bank, load_metaphor_bank, load_schema_bank
from sv_sdk.validators import validate_gold

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "gold_small.jsonl"


def test_load_gold_jsonl_round_trip() -> None:
    gold = load_gold_jsonl(FIXTURE)
    assert len(gold) == 2

    first = gold[0]
    assert first.id == "gold_1"
    assert first.labels.schemas[0].spans == [(5, 10), (22, 28)]
    # Ensure provenance was captured even when provided at top level
    assert first.provenance.curator == "QA"


def test_validate_gold_happy_path() -> None:
    gold = load_gold_jsonl(FIXTURE)
    errors, warnings = validate_gold(
        gold,
        load_schema_bank(),
        load_metaphor_bank(),
        load_frame_bank(),
        load_beats_config(),
        errors_as="list",
    )
    assert errors == []
    assert warnings == []


def test_load_gold_jsonl_rejects_bad_span(tmp_path: Path) -> None:
    path = tmp_path / "bad_span.jsonl"
    path.write_text(
        (
            '{"id": "bad", "lang": "en", "text": "abc", '
            '"labels": {"schemas": [{"id": "path", "spans": [[1, 1]]}], '
            '"metaphors": [], "attention": [], "explosion": null, '
            '"frame": null, "viewpoint": null}, '
            '"provenance": {"curator": "QA", "source": "fixture", '
            '"license": "CC0", "confidence": 0.5}}\n'
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="span end must be greater than start"):
        load_gold_jsonl(path)


def test_validate_gold_reports_unknowns(tmp_path: Path) -> None:
    path = tmp_path / "bad_refs.jsonl"
    path.write_text(
        (
            '{"id": "bad_refs", "lang": "en", "text": "abcde", '
            '"labels": {'
            '"schemas": [{"id": "not_real", "spans": [[0, 5]]}], '
            '"metaphors": [{"id": "life_is_travel", "spans": [[0, 3]]}], '
            '"frame": {"id": "journey"}, '
            '"viewpoint": {"person": "3rd", "tense": "present", "distance": "medium"}, '
            '"attention": [{"span": [0, 3], "w": 0.5}], '
            '"explosion": {"beat": 7, "confidence": 0.4}}, '
            '"provenance": {"curator": "QA", "source": "fixture", '
            '"license": "CC0", "confidence": 0.5}}\n'
        ),
        encoding="utf-8",
    )

    gold = load_gold_jsonl(path)
    errors, _ = validate_gold(
        gold,
        load_schema_bank(),
        load_metaphor_bank(),
        load_frame_bank(),
        load_beats_config(),
        errors_as="list",
    )
    joined = "\n".join(errors)
    assert "unknown schema 'not_real'" in joined
    assert "explosion beat 7" in joined
