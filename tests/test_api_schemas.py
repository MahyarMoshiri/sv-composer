from fastapi.testclient import TestClient

from sv_api.main import app

client = TestClient(app)


def test_schemas_envelope_and_summary() -> None:
    response = client.get("/bible/schemas")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    data = payload["data"]
    assert "summary" in data
    assert "schemas" in data
    assert isinstance(data["schemas"], list)


def test_schemas_filter_by_id() -> None:
    response = client.get("/bible/schemas", params={"id": "container"})
    assert response.status_code == 200
    items = response.json()["data"]["schemas"]
    assert items
    assert all(item["id"] == "container" for item in items)


def test_schemas_validate_ok() -> None:
    response = client.get("/bible/schemas", params={"validate": True})
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["errors"] == []


def test_schemas_normalized_ok(normalized_schemas_file) -> None:  # noqa: ANN001 - fixture
    response = client.get("/bible/schemas", params={"source": "normalized"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["schemas"], "expected schemas list from normalized source"


def test_schemas_normalized_missing(remove_normalized_schemas) -> None:  # noqa: ANN001 - fixture
    response = client.get("/bible/schemas", params={"source": "normalized"})
    assert response.status_code == 422
    payload = response.json()
    assert payload["ok"] is False
    assert payload["errors"], "expected error messages when normalized data missing"


def test_schema_compatibility_envelope() -> None:
    response = client.get("/bible/schemas/compat")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    compat = payload["data"]["compat"]
    assert isinstance(compat, dict)
    assert compat


def test_schema_compatibility_normalized_missing(remove_normalized_schemas) -> None:  # noqa: ANN001
    response = client.get("/bible/schemas/compat", params={"source": "normalized"})
    assert response.status_code == 422
    payload = response.json()
    assert payload["ok"] is False
    assert payload["errors"], "expected error payload"
