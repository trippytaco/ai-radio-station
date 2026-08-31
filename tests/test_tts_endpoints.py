"""/tts/providers and /tts/switch endpoints."""
import radio_api
import tts_service


def test_list_tts_providers(client):
    resp = client.get("/tts/providers")
    assert resp.status_code == 200
    body = resp.json()
    assert body["current"] == "google"
    assert set(body["available"]) == {"google", "elevenlabs"}
    assert body["hosts"]["alex"] == "alex_female"


def test_switch_rejects_unknown_provider(client):
    resp = client.post("/tts/switch", params={"provider": "not-a-provider"})
    assert resp.status_code == 400


def test_switch_updates_current_provider(client, monkeypatch):
    class DummyProvider:
        async def synthesize(self, text, voice_id):
            return b"audio"

    monkeypatch.setattr(tts_service.TTSFactory, "get_provider", staticmethod(lambda name=None: DummyProvider()))

    resp = client.post("/tts/switch", params={"provider": "elevenlabs"})
    assert resp.status_code == 200
    assert resp.json()["provider"] == "elevenlabs"

    # regression: this must actually take effect, not just echo back
    assert radio_api.TTS_PROVIDER == "elevenlabs"
    assert client.get("/tts/providers").json()["current"] == "elevenlabs"
    assert client.get("/health").json()["tts_provider"] == "elevenlabs"


def test_switch_surfaces_provider_init_failure(client, monkeypatch):
    def boom(name=None):
        raise RuntimeError("ELEVENLABS_API_KEY not set in environment")

    monkeypatch.setattr(tts_service.TTSFactory, "get_provider", staticmethod(boom))

    resp = client.post("/tts/switch", params={"provider": "elevenlabs"})
    assert resp.status_code == 500
    assert "ELEVENLABS_API_KEY" in resp.json()["detail"]
