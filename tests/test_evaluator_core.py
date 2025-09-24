"""Unit tests for the deterministic evaluator."""
from __future__ import annotations

import copy
from pathlib import Path

import pytest

from sv_compose.controller import get_thresholds_config
from sv_eval.evaluator import evaluate
from sv_sdk.loader import load_frame_bank, load_metaphor_bank, load_schema_bank


@pytest.fixture(scope="module")
def thresholds() -> dict:
    return get_thresholds_config()


@pytest.fixture(scope="module")
def banks() -> dict:
    return {
        "schemas": load_schema_bank(),
        "metaphors": load_metaphor_bank(),
        "frames": load_frame_bank(),
    }


@pytest.fixture()
def base_trace() -> dict:
    curve_after = [0.25, 0.55, 0.68, 0.88, 0.94, 1.0]
    curve_before = [0.1, 0.35, 0.5, 0.7, 0.85, 0.95]
    metaphor_cycle = ["life_is_travel", "time_is_motion"]
    beats = []
    for index, beat_name in enumerate(["hook", "setup", "development", "turn", "reveal", "settle"]):
        metaphor = metaphor_cycle[index % len(metaphor_cycle)]
        beats.append(
            {
                "beat": beat_name,
                "selected_schemas": ["path"],
                "selected_metaphors": [metaphor],
            }
        )
    return {
        "frame_id": "journey",
        "beats": beats,
        "curve_before": curve_before,
        "curve_after": curve_after,
    }


def test_evaluator_passes_within_thresholds(thresholds: dict, banks: dict, base_trace: dict) -> None:
    trace = copy.deepcopy(base_trace)
    piece = "we climb the narrow stairs toward the tunnel\nthe dusk writes on our backs"

    result = evaluate(piece, trace, thresholds, banks)

    assert result["pass"] is True
    assert result["critical_violations"] == []
    assert result["penalties_applied"] == []
    assert result["metrics"]["schema_cov"] >= 0.6
    assert result["trace_echo"]["turn_index"] == 3


def test_evaluator_applies_over_length_penalty(thresholds: dict, banks: dict, base_trace: dict) -> None:
    trace = copy.deepcopy(base_trace)
    long_piece = "\n".join([f"line {n}" for n in range(12)])

    result = evaluate(long_piece, trace, thresholds, banks)

    penalty_codes = {entry["code"] for entry in result["penalties_applied"]}
    assert "over_length" in penalty_codes
    assert result["pass"] is False
    assert any(reason.startswith("metric schema_cov") for reason in result["reasons"])


def test_evaluator_flags_explosion_outside_turn(thresholds: dict, banks: dict, base_trace: dict) -> None:
    trace = copy.deepcopy(base_trace)
    trace["curve_after"] = [0.3, 0.88, 0.9, 0.7, 0.85, 1.0]
    piece = "we climb the narrow stairs toward the tunnel\nthe dusk writes on our backs"

    result = evaluate(piece, trace, thresholds, banks)

    assert result["pass"] is False
    assert "explosion_outside_turn" in result["critical_violations"]
    assert any("explosion" in reason for reason in result["reasons"])
