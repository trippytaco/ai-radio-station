"""
/generate/host-segment - the Claude-backed host banter endpoint.

Regression coverage for the bugs found/fixed on 2026-08-31:
- retired model id (claude-3-5-sonnet-20241022 -> claude-sonnet-5)
- missing ANTHROPIC_API_KEY not surfaced clearly
- non-200 / malformed Anthropic responses not surfaced clearly
"""
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
