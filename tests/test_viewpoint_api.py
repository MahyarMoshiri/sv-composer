from fastapi.testclient import TestClient

from sv_api.main import app

client = TestClient(app)


def test_viewpoint_detects_first_person() -> None:
    response = client.post(
        "/control/viewpoint",
        json={"prompt": "I walk across the bridge", "lang": "en"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    data = payload["data"]
    assert data["viewpoint"]["person"] == "1st"
    assert data["attention"], "expected attention peaks for lexical cues"


def test_viewpoint_detects_past_tense() -> None:
    response = client.post(
        "/control/viewpoint",
        json={"prompt": "yesterday we crossed the old corridor", "lang": "en"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["viewpoint"]["tense"] == "past"


def test_viewpoint_detects_close_distance() -> None:
    response = client.post(
        "/control/viewpoint",
        json={"prompt": "inside the room they whisper", "lang": "en"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["viewpoint"]["distance"] == "close"


def test_viewpoint_uses_frame_defaults_when_absent() -> None:
    response = client.post(
        "/control/viewpoint",
        json={"prompt": "A still tableau", "frame_id": "journey", "lang": "en"},
    )
    assert response.status_code == 200
    payload = response.json()
    hint = payload["data"]["viewpoint"]
    assert hint == {"person": "3rd", "tense": "present", "distance": "far"}


def test_viewpoint_handles_farsi_rules() -> None:
    response = client.post(
        "/control/viewpoint",
        json={"prompt": "\u0645\u0627 \u062f\u06cc\u0631\u0648\u0632 \u0627\u0632 \u0627\u062a\u0627\u0642 \u06af\u0630\u0634\u062a\u06cc\u0645", "lang": "fa"},
    )
    assert response.status_code == 200
    payload = response.json()
    hint = payload["data"]["viewpoint"]
    assert hint["person"] == "1st"
    assert hint["tense"] == "past"
    assert hint["distance"] == "close"
