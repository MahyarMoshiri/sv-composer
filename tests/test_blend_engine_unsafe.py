from __future__ import annotations

from sv_blend.blend import SceneActive, blend
from sv_sdk.loader import load_blend_rules


def test_blend_rejects_polar_conflict_without_explosion() -> None:
    rules = load_blend_rules()
    active = SceneActive(
        schemas=["path", "boundary"],
        metaphors=["life_is_travel", "raw_cooked"],
        poles={"raw_cooked": "raw|cooked"},
        gates=["bridge"],
        frame_id="journey",
        explosion_fired=False,
    )

    result = blend(active, rules)

    assert result["accepted"] is False
    assert result["score_final"] < rules.scoring.accept_threshold
    reasons = {entry["reason"] for entry in result["audit"]["penalties"]}
    assert "polar_conflict:raw_cooked" in reasons


def test_blend_allows_polar_conflict_after_explosion() -> None:
    rules = load_blend_rules()
    active = SceneActive(
        schemas=["path", "boundary"],
        metaphors=["life_is_travel", "raw_cooked"],
        poles={"raw_cooked": "raw|cooked"},
        gates=["bridge"],
        frame_id="journey",
        explosion_fired=True,
    )

    result = blend(active, rules)

    assert result["accepted"] is True
    assert result["score_final"] >= rules.scoring.accept_threshold
    reasons = {entry["reason"] for entry in result["audit"]["penalties"]}
    assert "polar_conflict:raw_cooked" not in reasons


def test_blend_depth_overflow_penalty() -> None:
    rules = load_blend_rules()
    active = SceneActive(
        schemas=["path", "boundary", "goal"],
        metaphors=["life_is_travel", "raw_cooked"],
        poles={"raw_cooked": "raw"},
        gates=["bridge"],
        frame_id="journey",
        explosion_fired=False,
    )

    result = blend(active, rules)

    assert result["accepted"] is False
    reasons = {entry["reason"] for entry in result["audit"]["penalties"]}
    assert "depth_overflow" in reasons
    assert result["score_final"] < rules.scoring.accept_threshold
