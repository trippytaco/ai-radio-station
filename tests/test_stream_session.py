"""/stream/session - the end-to-end NDJSON session stream."""
import json

import httpx
import radio_api
import respx


class StubPlexClient:
    async def get_library_tracks(self, library_key, limit=100):
        return [{"artist": "A", "title": "T", "album": "Al", "duration": 30, "stream_url": "u"}]


class StubNewsService:
    async def get_random_headline(self):
        return {"title": "Big news", "source": "BBC News", "description": "d", "url": "u"}


@respx.mock
def test_stream_session_returns_ndjson_segments(client, monkeypatch):
    monkeypatch.setattr(radio_api, "plex_client", StubPlexClient())
    monkeypatch.setattr(radio_api, "news_service", StubNewsService())
    monkeypatch.setattr("random.random", lambda: 0.1)  # deterministic: always music

    respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=httpx.Response(200, json={"content": [{"type": "text", "text": "banter"}]})
    )

    resp = client.get("/stream/session", params={"duration_minutes": 1})

    assert resp.status_code == 200
    lines = [json.loads(l) for l in resp.text.strip().split("\n") if l.strip()]
    assert len(lines) >= 1
    assert lines[0]["type"] == "host_intro"
    assert any(l["type"] == "music" for l in lines)


@respx.mock
def test_stream_session_survives_no_integrations_configured(client, monkeypatch):
    """With Plex/news unavailable, the stream must still complete (not
    hang) rather than looping forever - see radio_queue's stall guard."""
    monkeypatch.setattr(radio_api, "plex_client", None)
    monkeypatch.setattr(radio_api, "news_service", None)

    resp = client.get("/stream/session", params={"duration_minutes": 60})

    assert resp.status_code == 200
    lines = [json.loads(l) for l in resp.text.strip().split("\n") if l.strip()]
    assert lines[0]["type"] == "host_intro"
