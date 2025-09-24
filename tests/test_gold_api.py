from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import sv_api.routers.gold as gold_router
from sv_api.main import app

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "gold_small.jsonl"


def test_gold_stats_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(gold_router, "DEFAULT_GOLD_PATH", FIXTURE)

    client = TestClient(app)
    response = client.get("/gold/stats")
    assert response.status_code == 200

    payload = response.json()
    assert payload["ok"] is True
    data = payload["data"]

    assert data["count"] == 2
    assert data["by_lang"]["en"] == 1
    assert data["by_lang"]["fa"] == 1
    assert "sha256" in data
    assert "bible_version" in data
