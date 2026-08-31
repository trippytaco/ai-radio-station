"""
TTS provider factory/switching unit tests.

Regression coverage: /tts/switch used to update a config dict entry that
get_tts_provider() never read (it caches a single global instance from
the first call and never revisits env/config), so switching providers via
the API had zero effect on subsequent generations.
"""
import pytest

import tts_service
from tts_service import TTSFactory, get_tts_provider, set_provider


class DummyProvider:
    def __init__(self, name):
        self.name = name

    async def synthesize(self, text, voice_id):
        return f"{self.name}:{text}".encode()


@pytest.fixture(autouse=True)
def reset_factory_and_global():
    TTSFactory._providers = {}
    tts_service._tts_provider = None
    yield
    TTSFactory._providers = {}
    tts_service._tts_provider = None


def test_get_tts_provider_caches_instance(monkeypatch):
    calls = {"n": 0}

    def fake_get_provider(name=None):
        calls["n"] += 1
        return DummyProvider("google")

    monkeypatch.setattr(TTSFactory, "get_provider", staticmethod(fake_get_provider))

    p1 = get_tts_provider()
    p2 = get_tts_provider()

    assert p1 is p2
    assert calls["n"] == 1


def test_set_provider_replaces_cached_instance(monkeypatch):
    def fake_get_provider(name=None):
        return DummyProvider(name or "default")

    monkeypatch.setattr(TTSFactory, "get_provider", staticmethod(fake_get_provider))

    first = get_tts_provider()
    assert isinstance(first, DummyProvider)

    switched = set_provider("elevenlabs")

    assert switched.name == "elevenlabs"
    # subsequent get_tts_provider() calls must see the switched instance,
    # not silently keep serving the pre-switch one
    assert get_tts_provider() is switched
    assert get_tts_provider() is not first


def test_unknown_provider_raises():
    with pytest.raises(RuntimeError):
        TTSFactory.get_provider("not-a-real-provider")


def test_google_provider_requires_credentials_env(monkeypatch):
    from tts_service import GoogleCloudTTS
    # The google-cloud-texttospeech package isn't installed in this test
    # env; force the availability flag so we reach the credentials check
    # this test actually targets, rather than the "not installed" branch.
    monkeypatch.setattr(tts_service, "GOOGLE_AVAILABLE", True)
    monkeypatch.delenv("GOOGLE_CLOUD_CREDENTIALS_JSON", raising=False)

    with pytest.raises(RuntimeError, match="GOOGLE_CLOUD_CREDENTIALS_JSON"):
        GoogleCloudTTS()


def test_google_provider_accepts_base64_credentials(monkeypatch):
    """
    Regression test: GOOGLE_CLOUD_CREDENTIALS_JSON used to be treated as a
    file path (GOOGLE_APPLICATION_CREDENTIALS = <value>), but this deploy
    has no persistent file storage to point that at - it must accept the
    service account key's JSON content directly (base64-encoded, to
    survive a single-line Portainer env var field).
    """
    import base64
    from tts_service import GoogleCloudTTS

    monkeypatch.setattr(tts_service, "GOOGLE_AVAILABLE", True)
    fake_key = base64.b64encode(b'{"type": "service_account", "project_id": "x"}').decode()
    monkeypatch.setenv("GOOGLE_CLOUD_CREDENTIALS_JSON", fake_key)

    # Reaches real google-auth/google-cloud-texttospeech code past the
    # point this test cares about (JSON was parsed successfully) - those
    # aren't installed in this test env, so assert we got past parsing
    # rather than mocking the whole google client stack.
    with pytest.raises(Exception) as exc_info:
        GoogleCloudTTS()
    assert "must be the service account key's JSON" not in str(exc_info.value)


def test_google_provider_rejects_a_file_path(monkeypatch):
    """The old (wrong) usage - a file path - must fail with a clear
    message telling the caller what actually changed, not a cryptic
    JSON-decode error."""
    from tts_service import GoogleCloudTTS

    monkeypatch.setattr(tts_service, "GOOGLE_AVAILABLE", True)
    monkeypatch.setenv("GOOGLE_CLOUD_CREDENTIALS_JSON", "/path/to/service-account-key.json")

    with pytest.raises(RuntimeError, match="must be the service account key's JSON"):
        GoogleCloudTTS()


def test_google_provider_not_installed(monkeypatch):
    from tts_service import GoogleCloudTTS
    monkeypatch.setattr(tts_service, "GOOGLE_AVAILABLE", False)

    with pytest.raises(RuntimeError, match="not installed"):
        GoogleCloudTTS()


def test_elevenlabs_provider_requires_api_key(monkeypatch):
    from tts_service import ElevenLabsTTS
    monkeypatch.setattr(tts_service, "ELEVENLABS_AVAILABLE", True)
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="ELEVENLABS_API_KEY"):
        ElevenLabsTTS()


def test_elevenlabs_provider_not_installed(monkeypatch):
    from tts_service import ElevenLabsTTS
    monkeypatch.setattr(tts_service, "ELEVENLABS_AVAILABLE", False)

    with pytest.raises(RuntimeError, match="not installed"):
        ElevenLabsTTS()
