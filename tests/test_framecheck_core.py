from __future__ import annotations

from sv_eval.framecheck import (
    FRM_BEAT_AFFINITY_WEAK,
    FRM_DISALLOWED_METAPHOR,
    FRM_DISALLOWED_SCHEMA,
    FRM_GATE_NOT_ALLOWED,
    FRM_MISSING_REQUIRED_SCHEMA,
    FRM_VIEWPOINT_MISMATCH,
    check_frame,
)
from sv_sdk.loader import load_frame_bank


def _frame(frame_id: str):
    bank = load_frame_bank()
    for entry in bank.frames:
        if entry.id == frame_id:
            return entry
    raise AssertionError(f"frame {frame_id} not found in test data")


JOURNEY = _frame("journey")


def test_missing_required_schema_flags_violation() -> None:
    result = check_frame({}, JOURNEY)
    assert result["pass"] is False
    assert FRM_MISSING_REQUIRED_SCHEMA in result["reasons"]


def test_disallowed_schema_and_not_allowed_detected() -> None:
    adjusted = JOURNEY.model_copy(update={"disallowed_schemas": ["blocked"]})
    direct = check_frame({"schemas": ["path", "blocked"]}, adjusted)
    assert FRM_DISALLOWED_SCHEMA in direct["reasons"]

    not_allowed = check_frame({"schemas": ["path", "container"]}, JOURNEY)
    assert FRM_DISALLOWED_SCHEMA in not_allowed["reasons"]


def test_disallowed_metaphor_detected() -> None:
    adjusted = JOURNEY.model_copy(update={"disallowed_metaphors": ["life_is_travel"]})
    result = check_frame({"schemas": ["path"], "metaphors": ["life_is_travel"]}, adjusted)
    assert FRM_DISALLOWED_METAPHOR in result["reasons"]


def test_gate_not_allowed_detected() -> None:
    result = check_frame({"schemas": ["path"], "gates": ["ladder"]}, JOURNEY)
    assert FRM_GATE_NOT_ALLOWED in result["reasons"]


def test_viewpoint_mismatch_when_no_explicit_cue() -> None:
    result = check_frame(
        {
            "schemas": ["path"],
            "viewpoint": {"person": "1st", "tense": "present", "distance": "medium"},
        },
        JOURNEY,
    )
    assert FRM_VIEWPOINT_MISMATCH in result["reasons"]
    assert result["pass"] is False


def test_viewpoint_explicit_override_prevents_mismatch() -> None:
    result = check_frame(
        {
            "schemas": ["path"],
            "viewpoint": {
                "person": "1st",
                "tense": "present",
                "distance": "medium",
                "explicit": True,
            },
        },
        JOURNEY,
    )
    assert FRM_VIEWPOINT_MISMATCH not in result["reasons"]
    assert result["pass"] is True


def test_beat_affinity_weak_is_informational() -> None:
    result = check_frame({"schemas": ["path"], "beats": ["hook"]}, JOURNEY)
    assert FRM_BEAT_AFFINITY_WEAK in result["reasons"]
    assert result["pass"] is True
