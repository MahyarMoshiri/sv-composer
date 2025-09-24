from __future__ import annotations

from fastapi.testclient import TestClient

from sv_api.main import app

client = TestClient(app)


def test_generate_endpoint_smoke() -> None:
    response = client.post(
        "/generate",
        json=
        {
            "frame_id": "journey",
            "query": "inside the room at dusk",
            "beats": ["hook", "setup", "development", "turn", "reveal", "settle"],
            "llm": "echo",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    data = payload["data"]
    assert isinstance(data["final"], str) and data["final"].strip()
    beats = data["beats"]
    for beat in ["hook", "setup", "development", "turn", "reveal", "settle"]:
        assert beat in beats
        assert "candidate" in beats[beat]
        assert "final" in beats[beat]
    assert "critique" in data["trace"]
