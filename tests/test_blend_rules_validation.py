from __future__ import annotations

import pytest

from sv_sdk.loader import (
    load_blend_rules,
    load_frame_bank,
    load_metaphor_bank,
    load_schema_bank,
)
from sv_sdk.models import BlendRules
from sv_sdk.validators import validate_blend_rules


def _banks():
    return (
        load_frame_bank(),
        load_schema_bank(),
        load_metaphor_bank(),
    )


def test_blend_rules_validate_ok() -> None:
    rules = load_blend_rules()
    frames, schemas, metaphors = _banks()
    validate_blend_rules(rules, frames, schemas, metaphors)


def test_blend_rules_operator_cost_out_of_range() -> None:
    original = load_blend_rules()
    raw = original.model_dump(mode="python", by_alias=True)
    raw["operators"][0]["cost"] = 1.25
    bad = BlendRules(**raw)
    frames, schemas, metaphors = _banks()
    with pytest.raises(ValueError, match="operator .* cost .* outside"):
        validate_blend_rules(bad, frames, schemas, metaphors)


def test_blend_rules_unknown_frame_override() -> None:
    original = load_blend_rules()
    raw = original.model_dump(mode="python", by_alias=True)
    raw.setdefault("frame_overrides", {})["unknown_frame"] = {"prefer_relations": ["role"]}
    bad = BlendRules(**raw)
    frames, schemas, metaphors = _banks()
    with pytest.raises(ValueError, match="frame_overrides references unknown frame"):
        validate_blend_rules(bad, frames, schemas, metaphors)


def test_blend_rules_unknown_schema_in_ban() -> None:
    original = load_blend_rules()
    raw = original.model_dump(mode="python", by_alias=True)
    raw.setdefault("constraints", {}).setdefault("banned_schema_pairs", []).append(["path", "unknown_schema"])
    bad = BlendRules(**raw)
    frames, schemas, metaphors = _banks()
    with pytest.raises(ValueError, match="banned_schema_pairs"):
        validate_blend_rules(bad, frames, schemas, metaphors)
