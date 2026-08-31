"""Basic liveness and config endpoints."""


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "ai-radio-station"
    assert "timestamp" in body


def test_get_config_returns_defaults(client):
    resp = client.get("/config")
    assert resp.status_code == 200
    body = resp.json()
    assert body["host_personality"] == "alex"
    assert body["music_weight"] == 0.5


def test_update_config_merges_and_persists(client):
    resp = client.post("/config", json={"host_personality": "jordan"})
    assert resp.status_code == 200
    assert resp.json()["config"]["host_personality"] == "jordan"

    # persisted for subsequent requests
    resp2 = client.get("/config")
    assert resp2.json()["host_personality"] == "jordan"

    # untouched keys survive the merge
    assert resp2.json()["music_weight"] == 0.5


def test_update_config_updates_queue_weights(client):
    import radio_api

    client.post("/config", json={"music_weight": 0.9, "news_weight": 0.05, "ad_weight": 0.05})
    assert radio_api.radio_queue.music_weight == 0.9
    assert radio_api.radio_queue.news_weight == 0.05
    assert radio_api.radio_queue.ad_weight == 0.05
