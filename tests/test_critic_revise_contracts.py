from __future__ import annotations

from sv_compose.generate import assemble, critique, revise
from sv_llm import EchoLLM

CTX = {
    "frame": {"id": "journey", "definition": "Movement…"},
    "active": {
        "schemas": ["path", "boundary"],
        "metaphors": ["life_is_travel"],
        "poles": {"raw_cooked": "raw"},
    },
    "beat": {
        "name": "turn",
        "goal": "reveal counter-pole",
        "expectation_target": 0.85,
        "min_chars": 35,
        "max_chars": 140,
        "constraints": {
            "ban_tokens": ["blood", "neon"],
        },
    },
    "thresholds": {
        "form": {"max_chars": 680, "max_lines": 8},
    },
}


def test_critic_detects_over_length_and_revise_trims() -> None:
    candidate = "inside the kiln the shadows gather" * 6
    critic = critique(candidate, CTX)
    assert "\"pass\"" in critic["prompt"]
    result = critic["result"]
    assert result["pass"] is False
    assert "OVER_LENGTH" in result["violations"]

    llm = EchoLLM()
    revised = revise(candidate, result, CTX, llm)
    assert revised
    assert len(revised) < len(candidate)


def test_assemble_respects_limits() -> None:
    beats = {
        "hook": "line one",
        "turn": "line two",
        "settle": "line three",
    }
    final = assemble(beats, CTX)
    assert final.count("\n") < CTX["thresholds"]["form"]["max_lines"]
    assert len(final) <= CTX["thresholds"]["form"]["max_chars"]
