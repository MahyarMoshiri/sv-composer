from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from sv_api.main import app
from sv_sdk.loader import load_metaphor_bank
from sv_sdk.validators import validate_metaphor_bank

client = TestClient(app)


def test_lexeme_weight_range_enforced() -> None:
    bank = load_metaphor_bank()
    mutated = bank.model_copy(deep=True)
    mutated.metaphors[0].lexicon.en[0].w = 1.5
    with pytest.raises(ValueError) as excinfo:
        validate_metaphor_bank(mutated)
    assert "weight" in str(excinfo.value)


def test_unknown_schema_reference(monkeypatch: pytest.MonkeyPatch) -> None:
    bank = load_metaphor_bank()
    mutated = bank.model_copy(deep=True)
    mutated.metaphors[0].coactivate_schemas.append("unknown_schema")

    monkeypatch.setattr(
        "sv_api.routers.bible_metaphors.load_metaphor_bank", lambda: mutated
    )

    response = client.get("/bible/metaphors", params={"validate": True})
    assert response.status_code == 422
    payload = response.json()
    assert payload["ok"] is False
    message = "\n".join(payload["errors"])
    assert "unknown schema" in message
