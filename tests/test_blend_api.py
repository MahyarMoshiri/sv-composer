from __future__ import annotations

from fastapi.testclient import TestClient

from sv_api.main import app

client = TestClient(app)


def test_blend_rules_endpoint_validates() -> None:
    response = client.get("/bible/blend_rules", params={"validate": True})
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert isinstance(payload["warnings"], list)
    summary = payload["data"]["summary"]
    assert "version" in summary
    assert summary["operators"] > 0


def test_blend_endpoint_accepts_safe_payload() -> None:
    body = {
        "frame_id": "journey",
        "active": {
            "schemas": ["path", "boundary"],
            "metaphors": ["life_is_travel", "raw_cooked"],
            "poles": {"raw_cooked": "raw"},
            "gates": ["bridge"],
        },
        "explosion_fired": False,
    }

    response = client.post("/blend", json=body)
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["warnings"] == []
    data = payload["data"]
    assert data["accepted"] is True
    assert data["decisions"]["operators"] == ["projection", "composition"]
    assert data["score_final"] >= data["audit"]["thresholds"]["accept"]


def test_blend_endpoint_polar_conflict_depends_on_explosion() -> None:
    base_active = {
        "schemas": ["path", "boundary"],
        "metaphors": ["life_is_travel", "raw_cooked"],
        "poles": {"raw_cooked": "raw|cooked"},
        "gates": ["bridge"],
    }

    response = client.post(
        "/blend",
        json={"frame_id": "journey", "active": base_active, "explosion_fired": False},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["accepted"] is False
    assert "penalties_applied" in payload["warnings"]

    response = client.post(
        "/blend",
        json={"frame_id": "journey", "active": base_active, "explosion_fired": True},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["accepted"] is True
