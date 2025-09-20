from fastapi.testclient import TestClient

from sv_api.main import app

client = TestClient(app)


def test_lexicon_matches() -> None:
    response = client.get("/bible/schemas/lexicon", params={"lang": "en", "text": "inside"})
    assert response.status_code == 200
    data = response.json()
    assert data["matches"], "Expected non-empty matches"
    assert isinstance(data["matches"], dict)
