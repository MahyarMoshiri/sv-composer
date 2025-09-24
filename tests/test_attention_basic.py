from fastapi.testclient import TestClient

from sv_api.main import app

client = TestClient(app)


def test_attention_highlights_container_cues() -> None:
    response = client.post(
        "/control/attention",
        json={"text": "inside room", "lang": "en"},
    )
    assert response.status_code == 200
    payload = response.json()
    peaks = payload["data"]["attention"]
    assert any(peak["token"] == "container" and peak["w"] > 0 for peak in peaks)


def test_attention_highlights_path_like_cues() -> None:
    response = client.post(
        "/control/attention",
        json={"text": "across the bridge", "lang": "en"},
    )
    assert response.status_code == 200
    payload = response.json()
    peaks = payload["data"]["attention"]
    assert any(
        peak["token"] in {"path", "boundary", "link"} and peak["w"] > 0
        for peak in peaks
    ), "expected path-adjacent schema weight"


def test_attention_supports_farsi_cues() -> None:
    response = client.post(
        "/control/attention",
        json={"text": "\u062f\u0631\u0648\u0646 \u0627\u062a\u0627\u0642", "lang": "fa"},
    )
    assert response.status_code == 200
    peaks = response.json()["data"]["attention"]
    assert any(peak["token"] == "container" and peak["w"] > 0 for peak in peaks)
