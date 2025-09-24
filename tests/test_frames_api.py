from fastapi.testclient import TestClient

from sv_api.main import app

client = TestClient(app)


def test_frames_envelope_and_summary() -> None:
    response = client.get("/bible/frames")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    data = payload["data"]
    assert "summary" in data
    assert "frames" in data
    assert isinstance(data["frames"], list)


def test_frames_filter_by_id() -> None:
    response = client.get("/bible/frames", params={"id": "journey"})
    assert response.status_code == 200
    items = response.json()["data"]["frames"]
    assert items
    assert all(item["id"] == "journey" for item in items)


def test_frames_validate_ok() -> None:
    response = client.get("/bible/frames", params={"validate": True})
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["errors"] == []
    warnings = payload["data"].get("warnings", [])
    assert isinstance(warnings, list)
