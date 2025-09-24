from __future__ import annotations

import json
import pathlib

from sv_compose.render import render_template

CTX = {
    "frame": {"id": "journey", "definition": "Movement…"},
    "active": {"schemas": ["path", "boundary"], "metaphors": ["life_is_travel"], "poles": {"raw_cooked": "raw"}},
    "beat": {
        "name": "turn",
        "goal": "reveal counter-pole",
        "expectation_target": 0.85,
        "min_chars": 30,
        "max_chars": 140,
        "constraints": {},
    },
    "candidate": "she crosses the narrow bridge into the darker room",
    "thresholds": {"accept_threshold": 0.7},
    "beats": [
        {"name": "hook", "expectation_target": 0.2},
        {"name": "setup", "expectation_target": 0.4},
        {"name": "development", "expectation_target": 0.6},
        {"name": "turn", "expectation_target": 0.85},
        {"name": "reveal", "expectation_target": 0.9},
        {"name": "settle", "expectation_target": 1.0},
    ],
}


def test_critic_renders_json_contract() -> None:
    template_path = pathlib.Path("prompts/templates/critic.md")
    out = render_template(template_path, CTX)
    assert "Output Contract" not in out
    assert "pass" in out and "metrics" in out


def test_revise_renders_lines_contract() -> None:
    template_path = pathlib.Path("prompts/templates/revise.md")
    context = CTX | {"critic_json": json.dumps({"pass": False, "reasons": ["OVER_LENGTH"]})}
    out = render_template(template_path, context)
    assert isinstance(out, str)
    assert out.strip()


def test_beat_plan_renders_json() -> None:
    template_path = pathlib.Path("prompts/templates/beat_plan.md")
    context = CTX | {"beats": CTX["beats"]}
    out = render_template(template_path, context)
    assert "beats" in out
