import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from sv_api.main import app
from sv_p12.config import P12Config
from sv_p12.models import ScenePrompt
from sv_p12.render import render_sfx_prompt, render_video_prompt

client = TestClient(app)

SAMPLE_GENERATE = {
    "beats": {
        "hook": {"candidate": "", "final": "A doorway leaks a sliver of dawn."},
        "setup": {"candidate": "", "final": "The room breathes in shallow light."},
        "development": {"candidate": "", "final": "Footsteps explore the quiet path."},
        "turn": {"candidate": "", "final": "The door swings; light floods in."},
        "reveal": {"candidate": "", "final": "Dust motes flare in the beam."},
        "settle": {"candidate": "", "final": "The room exhales back to calm."},
    },
    "final": "",
    "trace": {
        "frame_id": "sleep_gate",
        "curve_before": [0.1, 0.2, 0.35, 0.45, 0.5, 0.55],
        "curve_after": [0.15, 0.25, 0.4, 0.8, 0.55, 0.57],
        "beats": [
            {
                "beat": "hook",
                "selected_schemas": ["boundary"],
                "selected_metaphors": ["light_dark"],
                "tokens": {"must": ["doorway"], "ban": ["logo"]},
                "prompts": {"context": "View from the threshold"},
                "plan": {"intent": "establish the threshold tension"},
            },
            {
                "beat": "setup",
                "selected_schemas": ["boundary"],
                "selected_metaphors": ["sleep_is_threshold"],
                "tokens": {"must": [], "ban": []},
                "prompts": {"context": "Calm interior"},
                "plan": {"intent": "establish the stakes"},
            },
            {
                "beat": "development",
                "selected_schemas": ["path"],
                "selected_metaphors": ["life_is_journey"],
                "tokens": {"must": ["footsteps"], "ban": []},
                "prompts": {"context": "Tracking along corridor"},
                "plan": {"intent": "build momentum"},
            },
            {
                "beat": "turn",
                "selected_schemas": ["boundary", "path"],
                "selected_metaphors": ["light_dark", "life_is_journey"],
                "tokens": {"must": [], "ban": ["blood"]},
                "prompts": {"context": "Door bursts open"},
                "plan": {"intent": "deliver the pivot"},
            },
            {
                "beat": "reveal",
                "selected_schemas": ["balance"],
                "selected_metaphors": ["light_dark"],
                "tokens": {"must": [], "ban": []},
                "prompts": {"context": "Light reveals detail"},
                "plan": {"intent": "show consequence"},
            },
            {
                "beat": "settle",
                "selected_schemas": ["boundary"],
                "selected_metaphors": ["sleep_is_threshold"],
                "tokens": {"must": [], "ban": []},
                "prompts": {"context": "Calm returns"},
                "plan": {"intent": "settle the energy"},
            },
        ],
    },
}


@pytest.fixture(autouse=True)
def patch_inference(monkeypatch):
    from sv_p12 import infer as infer_module

    class _FakeFrame:
        id = "sleep_gate"
        allowed_schemas = ["boundary", "path", "link", "balance"]
        viewpoint_defaults = SimpleNamespace(distance="medium")

    class _FakeIndex:
        frame_bank = SimpleNamespace(frames=[_FakeFrame()])

        def frame(self, frame_id):
            return _FakeFrame() if frame_id == "sleep_gate" else None

        def search(self, prompt, k=1, filter_kinds=None):
            return [SimpleNamespace(doc_id="sleep_gate")] if prompt else []

    monkeypatch.setattr(infer_module, "get_rag_index", lambda: _FakeIndex())
    monkeypatch.setattr(infer_module, "_call_generate", lambda frame_id, prompt, beats: SAMPLE_GENERATE)

    yield


def _post(payload):
    response = client.post("/p12/filmplan", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def test_prompt_only_equal_split():
    result = _post(
        {
            "prompt": "A hush before dawn: a thin door of light.",
            "total_duration_sec": 60,
            "scene_length_sec": 10,
            "allocation_mode": "EqualSplit",
        }
    )

    assert result["total_duration_sec"] == 60.0
    assert len(result["sequences"]) == 6
    for sequence in result["sequences"]:
        assert len(sequence["scenes"]) == 1
        assert sequence["scenes"][0]["duration_sec"] == 10.0


def test_prompt_only_curve_weighted_turn_up():
    result = _post(
        {
            "prompt": "A hush before dawn: a thin door of light.",
            "total_duration_sec": 80,
            "scene_length_sec": 10,
            "allocation_mode": "CurveWeighted",
        }
    )

    scene_counts = {seq["beat"]: len(seq["scenes"]) for seq in result["sequences"]}
    assert scene_counts["turn"] >= scene_counts["hook"]


def test_negative_prompt_merge():
    result = _post(
        {
            "prompt": "A hush before dawn: a thin door of light.",
            "total_duration_sec": 60,
            "scene_length_sec": 10,
        }
    )

    hook_scene = result["sequences"][0]["scenes"][0]
    negative = hook_scene["negative_prompt"].lower()
    assert "logo" in negative
    assert "violence" in negative


def test_llm_enrich_toggle(monkeypatch):
    enriched_values = {
        "camera": "stylized threshold composition",
        "lighting": "silver dawn rim",
        "color": "cool shadow wash",
        "motion": "air pulses softly",
    }
    monkeypatch.setattr(
        "sv_api.routers.p12.enrich_style_with_llm",
        lambda seed, cfg, temperature=None: enriched_values,
    )
    monkeypatch.setattr(
        "sv_api.routers.p12.load_p12_config",
        lambda: P12Config(api_key="test", model="stub", base_url=None, temperature=0.4),
    )

    base_result = _post(
        {
            "prompt": "A hush before dawn: a thin door of light.",
            "total_duration_sec": 60,
            "scene_length_sec": 10,
        }
    )
    base_camera = base_result["sequences"][0]["scenes"][0]["camera"]

    enriched_result = _post(
        {
            "prompt": "A hush before dawn: a thin door of light.",
            "total_duration_sec": 60,
            "scene_length_sec": 10,
            "llm_enrich": True,
        }
    )
    enriched_camera = enriched_result["sequences"][0]["scenes"][0]["camera"]
    assert enriched_camera != base_camera
    assert enriched_camera == enriched_values["camera"]


def test_aspect_ratio_and_renderers():
    result = _post(
        {
            "prompt": "A hush before dawn: a thin door of light.",
            "total_duration_sec": 60,
            "scene_length_sec": 10,
            "aspect_ratio": "9:16",
        }
    )

    scene = ScenePrompt(**result["sequences"][0]["scenes"][0])
    assert scene.aspect_ratio == "9:16"

    video_prompt = render_video_prompt(scene)
    sfx_prompt = render_sfx_prompt(scene)
    assert "[ASPECT]: 9:16" in video_prompt
    assert "[MOVEMENT]" in video_prompt
    assert "[AUDIO]" in sfx_prompt
