from fastapi.testclient import TestClient

from sv_api.main import app

client = TestClient(app)


def test_lexicon_scores_envelope(normalized_schemas_file) -> None:  # noqa: ANN001 - fixture
    response = client.get(
        "/bible/schemas/lexicon", params={"lang": "en", "text": "inside room"}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    data = payload["data"]
    assert data["lang"] == "en"
    assert data["text"] == "inside room"
    assert isinstance(data["scores"], dict)
