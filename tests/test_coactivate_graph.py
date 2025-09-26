from fastapi.testclient import TestClient

from sv_api.main import app
from sv_sdk.loader import load_schema_bank

client = TestClient(app)

def test_coactivate_targets_exist() -> None:
    bank = load_schema_bank()
    schema_ids = {schema.id for schema in bank.schemas}
    referenced = set()
    sources = set()

    for schema in bank.schemas:
        if schema.coactivate:
            sources.add(schema.id)
        for target in schema.coactivate:
            assert target in schema_ids
            referenced.add(target)

    active = sources | referenced
    assert active == schema_ids


def test_coactivate_graph_normalized_missing(remove_normalized_schemas) -> None:  # noqa: ANN001
    response = client.get("/bible/schemas/compat", params={"source": "normalized"})
    assert response.status_code == 422
    payload = response.json()
    assert payload["ok"] is False
    assert payload["errors"], "expected error payload"
