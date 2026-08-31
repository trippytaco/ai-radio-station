"""
Shared pytest fixtures.

The backend modules do same-directory imports (`from tts_service import
...`), matching how the container actually runs them (cwd = backend/), so
backend/ has to be on sys.path before anything under it is imported.
"""
import copy
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

# Dummy credentials so modules that read env vars at import time (e.g.
# ANTHROPIC_API_KEY, PLEX_TOKEN) get a defined value and the app starts up
# the same way it does in production. Individual tests that care about
# behavior stub the actual network calls - these are never sent anywhere.
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("PLEX_TOKEN", "test-plex-token")
os.environ.setdefault("PLEX_URL", "http://plex.test:32400")
os.environ.setdefault("LASTFM_API_KEY", "test-lastfm-key")
os.environ.setdefault("LASTFM_USERNAME", "test-user")

import pytest
from fastapi.testclient import TestClient

import radio_api
import tts_service


_DEFAULT_USER_CONFIG = copy.deepcopy(radio_api.user_config)


@pytest.fixture(autouse=True)
def reset_global_state():
    """
    radio_api keeps mutable state at module scope (user_config, the cached
    TTS provider instance). Reset it before every test so tests can't leak
    state into each other regardless of run order.
    """
    radio_api.user_config = copy.deepcopy(_DEFAULT_USER_CONFIG)
    radio_api.TTS_PROVIDER = os.environ.get("TTS_PROVIDER", "google")
    tts_service._tts_provider = None
    yield


@pytest.fixture
def client():
    with TestClient(radio_api.app) as c:
        yield c
