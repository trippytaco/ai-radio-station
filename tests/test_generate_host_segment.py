"""
/generate/host-segment - the Claude-backed host banter endpoint.

Regression coverage for the bugs found/fixed on 2026-08-31:
- retired model id (claude-3-5-sonnet-20241022 -> claude-sonnet-5)
- missing ANTHROPIC_API_KEY not surfaced clearly
- non-200 / malformed Anthropic responses not surfaced clearly
"""
import json

import httpx
import pytest
import respx

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


def _anthropic_success(text="Hey, it's your station, let's make this count."):
    return httpx.Response(200, json={"content": [{"type": "text", "text": text}]})


@respx.mock
def test_generate_host_segment_success(client):
    route = respx.post(ANTHROPIC_URL).mock(return_value=_anthropic_success("Sassy banter incoming."))

    resp = client.post("/generate/host-segment", params={"context": "transition"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["text"] == "Sassy banter incoming."
    assert body["host"] == "Alex"
    assert body["context"] == "transition"
    assert route.called
    # regression guard: must not silently drift back to a retired model id
    sent_body = respx.calls.last.request.content
    assert b'"claude-sonnet-5"' in sent_body


@respx.mock
def test_generate_host_segment_uses_current_host_personality(client):
    client.post("/config", json={"host_personality": "jordan"})
    respx.post(ANTHROPIC_URL).mock(return_value=_anthropic_success())

    resp = client.post("/generate/host-segment", params={"context": "motivation"})

    assert resp.json()["host"] == "Jordan"


@respx.mock
def test_generate_host_segment_missing_api_key(client, monkeypatch):
    import radio_api
    monkeypatch.setattr(radio_api, "ANTHROPIC_API_KEY", None)

    resp = client.post("/generate/host-segment", params={"context": "intro"})

    assert resp.status_code == 500
    assert "ANTHROPIC_API_KEY" in resp.json()["detail"]


@respx.mock
def test_generate_host_segment_surfaces_anthropic_error(client):
    respx.post(ANTHROPIC_URL).mock(
        return_value=httpx.Response(404, json={"error": {"message": "model: claude-bogus-id"}})
    )

    resp = client.post("/generate/host-segment", params={"context": "intro"})

    assert resp.status_code == 500
    assert "404" in resp.json()["detail"]


@respx.mock
def test_generate_host_segment_handles_empty_content(client):
    respx.post(ANTHROPIC_URL).mock(return_value=httpx.Response(200, json={"content": []}))

    resp = client.post("/generate/host-segment", params={"context": "intro"})

    assert resp.status_code == 500
    assert "No content" in resp.json()["detail"]


@respx.mock
def test_generate_host_segment_degrades_gracefully_when_tts_fails(client):
    """TTS is best-effort - a TTS failure must not fail the whole request."""
    respx.post(ANTHROPIC_URL).mock(return_value=_anthropic_success("Text should still come back."))

    resp = client.post("/generate/host-segment", params={"context": "intro"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["text"] == "Text should still come back."
    # No TTS provider is configured in the test environment (no
    # GOOGLE_CLOUD_CREDENTIALS_JSON / ELEVENLABS_API_KEY), so this must
    # degrade to text-only rather than 500.
    assert body["audio_available"] is False
    assert body["audio_url"] is None


@respx.mock
def test_generate_host_segment_returns_playable_audio_url(client, monkeypatch):
    """
    Regression test: audio_bytes used to be synthesized and then discarded -
    the response only ever said audio_available: true/false with nothing a
    client could actually play. TTS success must now yield an audio_url
    that GET /audio/segment/{id} actually serves.
    """
    import radio_api

    class FakeTTSProvider:
        async def synthesize(self, text, voice_id):
            return b"fake-mp3-bytes"

    monkeypatch.setattr(radio_api, "get_tts_provider", lambda: FakeTTSProvider())
    respx.post(ANTHROPIC_URL).mock(return_value=_anthropic_success("Here's your audio."))

    resp = client.post("/generate/host-segment", params={"context": "intro"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["audio_available"] is True
    assert body["audio_url"].startswith("/audio/segment/")
    assert body["tts_provider"] == "google"

    audio_resp = client.get(body["audio_url"])
    assert audio_resp.status_code == 200
    assert audio_resp.headers["content-type"] == "audio/mpeg"
    assert audio_resp.content == b"fake-mp3-bytes"


def test_audio_segment_404_for_unknown_id(client):
    resp = client.get("/audio/segment/does-not-exist")
    assert resp.status_code == 404


@respx.mock
def test_generate_host_segment_safe_mode_and_topics_reach_the_prompt(client):
    """safe_mode/topics config should actually influence what's sent to
    Claude, not just be stored and ignored."""
    client.post("/config", json={"safe_mode": True, "topics": ["space", "cricket"]})
    respx.post(ANTHROPIC_URL).mock(return_value=_anthropic_success())

    client.post("/generate/host-segment", params={"context": "intro"})

    sent = json.loads(respx.calls.last.request.content)
    prompt = sent["messages"][0]["content"]
    assert "family-friendly" in prompt
    assert "space, cricket" in prompt


@respx.mock
def test_ad_lib_topic_hint_reaches_the_prompt(client):
    """A category hint (passed as topic) steers ad_lib generation, giving
    each ad a fresh angle instead of always producing similarly generic
    fake products."""
    respx.post(ANTHROPIC_URL).mock(return_value=_anthropic_success())

    client.post("/generate/host-segment", params={"context": "ad_lib", "topic": "kitchen gadgets"})

    sent = json.loads(respx.calls.last.request.content)
    prompt = sent["messages"][0]["content"]
    assert "kitchen gadgets" in prompt
    assert "brand name" in prompt
