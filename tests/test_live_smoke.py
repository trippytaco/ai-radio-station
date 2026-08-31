"""
Opt-in smoke tests against a REAL running instance (e.g. the deployed QNAP
container), rather than the in-process app with mocked external calls.

These hit real integrations (Anthropic, Plex, Last.fm, news, TTS) using
whatever credentials that instance actually has configured, so they're
expected to skip/tolerate 400s for integrations that aren't set up rather
than hard-failing the whole run.

Not run by default - the rest of the suite (everything else in tests/)
runs with zero network access and zero credentials. To run these:

    AI_RADIO_LIVE_URL=http://192.168.8.113:8000 \
        .venv-test/bin/pytest tests/test_live_smoke.py -v -m live

Every test is marked `live` and skipped automatically unless
AI_RADIO_LIVE_URL is set.
"""
import os

import httpx
import pytest

BASE_URL = os.environ.get("AI_RADIO_LIVE_URL")

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(not BASE_URL, reason="set AI_RADIO_LIVE_URL to run live smoke tests"),
]


@pytest.fixture
def live_client():
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as c:
        yield c


def test_health(live_client):
    resp = live_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_config_roundtrip(live_client):
    original = live_client.get("/config").json()
    try:
        resp = live_client.post("/config", json={"host_personality": "jordan"})
        assert resp.status_code == 200
        assert live_client.get("/config").json()["host_personality"] == "jordan"
    finally:
        # don't leave the live instance's config mutated by the test run
        live_client.post("/config", json=original)


def test_generate_host_segment(live_client):
    """Exercises the real Anthropic call end to end - this is the endpoint
    that was actually broken (retired model id) on 2026-08-31."""
    resp = live_client.post("/generate/host-segment", params={"context": "intro"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["text"]
    assert body["host"] in ("Alex", "Jordan")


def test_tts_providers_listed(live_client):
    resp = live_client.get("/tts/providers")
    assert resp.status_code == 200
    assert "google" in resp.json()["available"]


def test_plex_libraries_gracefully_handles_missing_config(live_client):
    resp = live_client.get("/plex/libraries")
    # Either it's configured and works, or it's not and says so clearly -
    # anything else (e.g. a raw 500 traceback) is a real bug.
    assert resp.status_code in (200, 400, 500)
    if resp.status_code != 200:
        assert resp.json().get("detail")


def test_lastfm_recent_gracefully_handles_missing_config(live_client):
    resp = live_client.get("/lastfm/recent")
    assert resp.status_code in (200, 400)


def test_news_headlines_gracefully_handles_missing_config(live_client):
    resp = live_client.get("/news/headlines")
    assert resp.status_code in (200, 500)


def test_stream_session_completes_quickly(live_client):
    """Regression guard for the SessionBuilder infinite-loop bug - a short
    session must return promptly, not hang."""
    resp = live_client.get("/stream/session", params={"duration_minutes": 1})
    assert resp.status_code == 200
    lines = [l for l in resp.text.strip().split("\n") if l.strip()]
    assert lines
