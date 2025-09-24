"""API smoke tests for the evaluator endpoints."""
from __future__ import annotations

import copy

from fastapi.testclient import TestClient

from sv_api.main import app


client = TestClient(app)


def _trace_payload() -> dict:
    metaphor_cycle = ["life_is_travel", "time_is_motion"]
    beats = []
    for index, beat_name in enumerate(["hook", "setup", "development", "turn", "reveal", "settle"]):
        beats.append(
            {
                "beat": beat_name,
                "selected_schemas": ["path"],
                "selected_metaphors": [metaphor_cycle[index % len(metaphor_cycle)]],
            }
        )
    base = {
        "frame_id": "journey",
        "beats": beats,
        "curve_after": [0.2, 0.45, 0.6, 0.86, 0.92, 1.0],
        "curve_before": [0.15, 0.3, 0.5, 0.7, 0.85, 0.95],
    }
    return copy.deepcopy(base)


def test_evaluate_endpoint_returns_envelope() -> None:
    payload = {
        "piece": "we climb the narrow stairs toward the tunnel\nthe dusk writes on our backs",
        "trace": _trace_payload(),
    }
    response = client.post("/evaluate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["ok"] is True
    assert data["errors"] == []
    result = data["data"]
    assert result["pass"] is True
    assert "metrics" in result
    assert "score_final" in result


def test_evaluate_batch_returns_results() -> None:
    base_trace = _trace_payload()
    items = [
        {"id": "pass", "piece": "stairs toward the tunnel", "trace": base_trace},
        {"id": "fail", "piece": "", "trace": base_trace},
    ]
    response = client.post("/evaluate/batch", json=items)
    assert response.status_code == 200

    data = response.json()
    assert data["ok"] is True
    results = {entry["id"]: entry for entry in data["data"]["results"]}
    assert "pass" in results and "fail" in results
    assert results["pass"]["result"]["pass"] is True
    assert results["fail"]["result"]["pass"] is False
