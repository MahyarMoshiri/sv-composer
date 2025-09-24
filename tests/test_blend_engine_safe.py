from __future__ import annotations

from sv_blend.blend import SceneActive, blend
from sv_sdk.loader import load_blend_rules


def test_blend_accepts_safe_configuration() -> None:
    rules = load_blend_rules()
    active = SceneActive(
        schemas=["path", "boundary"],
        metaphors=["life_is_travel", "raw_cooked"],
        poles={"raw_cooked": "raw"},
        gates=["bridge"],
        frame_id="journey",
        explosion_fired=False,
    )

    result = blend(active, rules)

    assert result["accepted"] is True
    assert result["score_final"] >= rules.scoring.accept_threshold
    assert result["decisions"]["operators"] == ["projection", "composition"]
    assert result["audit"]["penalties"] == []
