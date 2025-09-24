from fastapi.testclient import TestClient

from sv_api.main import app

client = TestClient(app)


def test_metaphors_envelope_and_summary() -> None:
    response = client.get("/bible/metaphors")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    data = payload["data"]
    assert "summary" in data
    assert data["summary"]["count"] >= len(data["metaphors"])
    assert "metaphors" in data


def test_metaphors_filter_by_id() -> None:
    response = client.get("/bible/metaphors", params={"id": "life_is_travel"})
    assert response.status_code == 200
    items = response.json()["data"]["metaphors"]
    assert items
    assert all(item["id"] == "life_is_travel" for item in items)


def test_metaphors_validate_ok() -> None:
    response = client.get("/bible/metaphors", params={"validate": True})
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["errors"] == []
    warnings = payload["data"].get("warnings", [])
    assert isinstance(warnings, list)
