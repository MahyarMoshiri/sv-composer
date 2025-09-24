from __future__ import annotations

from fastapi.testclient import TestClient

from sv_api.main import app

client = TestClient(app)


def test_compose_plan_and_full() -> None:
    response_plan = client.post(
        "/compose/plan",
        json={"frame_id": "journey", "query": "inside the room at dusk", "k": 6},
    )
    data_plan = response_plan.json()
    assert response_plan.status_code == 200
    assert data_plan["ok"] is True
    plan = data_plan["data"]["plan"]
    assert any(item.get("name") == "turn" for item in plan)

    response_compose = client.post(
        "/compose",
        json={
            "frame_id": "journey",
            "query": "inside the room at dusk",
            "beats": ["hook", "setup", "development", "turn", "reveal", "settle"],
        },
    )
    payload = response_compose.json()
    assert response_compose.status_code == 200
    assert payload["ok"] is True
    assert "beats" in payload["data"]["prompts"]
    assert "trace" in payload["data"]
