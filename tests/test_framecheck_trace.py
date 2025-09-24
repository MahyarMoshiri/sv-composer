from __future__ import annotations

from fastapi.testclient import TestClient

from sv_api.main import app
from sv_eval.framecheck import extract_active_from_trace

client = TestClient(app)


TRACE_SAMPLE = {
    "selected": {
        "schemas": ["path"],
        "metaphors": ["life_is_travel"],
        "gates": ["bridge"],
        "beats": ["turn"],
    },
    "steps": [
        {
            "step": 1,
            "vp": {"person": "3rd", "tense": "present", "distance": "medium"},
        }
    ],
}


def test_extract_active_from_trace_reads_selected_lists() -> None:
    state = extract_active_from_trace(TRACE_SAMPLE)
    assert state.schemas == {"path"}
    assert state.metaphors == {"life_is_travel"}
    assert state.gates == {"bridge"}
    assert state.beats == {"turn"}
    assert state.viewpoint["person"] == "3rd"


def test_framecheck_endpoint_accepts_trace_payload() -> None:
    response = client.post(
        "/eval/framecheck",
        json={"frame_id": "journey", "trace": TRACE_SAMPLE},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    data = payload["data"]
    assert data["pass"] is True
    assert data["reasons"] == []
