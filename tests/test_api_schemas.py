from fastapi.testclient import TestClient

from sv_api.main import app
from sv_sdk.loader import load_schema_bank

client = TestClient(app)


def test_get_schemas_summary() -> None:
    response = client.get("/bible/schemas")
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    summary = data["summary"]
    bank = load_schema_bank()
    assert summary["schemas_count"] == len(bank.schemas)
    assert "schemas" in data
    assert isinstance(data["schemas"], list)


def test_get_schema_by_id() -> None:
    response = client.get("/bible/schemas", params={"id": "container"})
    assert response.status_code == 200
    data = response.json()
    schemas = data["schemas"]
    assert len(schemas) == 1
    assert schemas[0]["id"] == "container"


def test_get_schema_compat() -> None:
    response = client.get("/bible/schemas/compat")
    assert response.status_code == 200
    data = response.json()
    bank = load_schema_bank()
    ids = {schema.id for schema in bank.schemas}
    assert set(data["compat"].keys()) == ids
