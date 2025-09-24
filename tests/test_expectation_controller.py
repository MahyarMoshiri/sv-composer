from fastapi.testclient import TestClient

from sv_api.main import app

client = TestClient(app)


DEFAULT_BEATS = ["hook", "setup", "development", "turn", "reveal", "settle"]


def test_expectation_no_active_metaphors() -> None:
    response = client.post(
        "/control/expectation",
        json={"beats": DEFAULT_BEATS, "active_metaphors": []},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    data = payload["data"]
    assert data["curve_before"] == data["curve_after"]
    fire = data["fire"]
    assert fire["beat_index"] == 3
    assert fire["reason"] == "within_window"


def test_expectation_with_bipolar_bias() -> None:
    response = client.post(
        "/control/expectation",
        json={
            "beats": DEFAULT_BEATS,
            "active_metaphors": ["raw_cooked"],
            "poles": {"raw_cooked": "raw"},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    data = payload["data"]
    before = data["curve_before"]
    after = data["curve_after"]
    assert after[3] > before[3]
    fire = data["fire"]
    assert fire["beat_index"] == 3
    assert fire["reason"] == "within_window"
