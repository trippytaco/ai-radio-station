"""
/plex/* and /lastfm/* endpoint routing and error handling.

These stub out the underlying PlexClient/httpx calls - PlexClient's own
XML-parsing behavior is covered in test_plex_client.py.
"""
import httpx
import radio_api
import respx


class StubPlexClient:
    def __init__(self, libraries=None, tracks=None, raise_on=None):
        self._libraries = libraries or []
        self._tracks = tracks or []
        self._raise_on = raise_on or set()

    async def get_libraries(self):
        if "libraries" in self._raise_on:
            raise RuntimeError("boom")
        return self._libraries

    async def get_library_tracks(self, library_key, limit=50):
        if "tracks" in self._raise_on:
            raise RuntimeError("boom")
        return self._tracks

    async def get_track_stream_url(self, rating_key):
        if "stream_url" in self._raise_on:
            raise RuntimeError("resolve failed")
        return f"http://plex.test:32400/library/parts/1/1/file.flac?X-Plex-Token=super-secret-token"

    async def get_track_art_url(self, rating_key):
        if "art_url" in self._raise_on:
            raise RuntimeError("resolve failed")
        return f"http://plex.test:32400/library/metadata/1/thumb?X-Plex-Token=super-secret-token"


def test_plex_libraries_not_configured(client, monkeypatch):
    monkeypatch.setattr(radio_api, "plex_client", None)
    resp = client.get("/plex/libraries")
    assert resp.status_code == 500
    assert "not available" in resp.json()["detail"]


def test_plex_libraries_success(client, monkeypatch):
    monkeypatch.setattr(radio_api, "plex_client", StubPlexClient(libraries=[{"key": "1", "title": "Music"}]))
    resp = client.get("/plex/libraries")
    assert resp.status_code == 200
    assert resp.json()["libraries"][0]["title"] == "Music"


def test_plex_libraries_upstream_error_becomes_500(client, monkeypatch):
    monkeypatch.setattr(radio_api, "plex_client", StubPlexClient(raise_on={"libraries"}))
    resp = client.get("/plex/libraries")
    assert resp.status_code == 500
    assert "Plex error" in resp.json()["detail"]


def test_plex_tracks_success(client, monkeypatch):
    monkeypatch.setattr(radio_api, "plex_client", StubPlexClient(tracks=[{"title": "Song"}]))
    resp = client.get("/plex/tracks")
    assert resp.status_code == 200
    assert resp.json()["tracks"][0]["title"] == "Song"


@respx.mock
def test_plex_stream_proxies_bytes_and_content_type(client, monkeypatch):
    monkeypatch.setattr(radio_api, "plex_client", StubPlexClient())
    respx.get("http://plex.test:32400/library/parts/1/1/file.flac").mock(
        return_value=httpx.Response(200, content=b"fake-flac-bytes", headers={"content-type": "audio/flac"})
    )

    resp = client.get("/plex/stream/85916")

    assert resp.status_code == 200
    assert resp.content == b"fake-flac-bytes"
    assert resp.headers["content-type"] == "audio/flac"


@respx.mock
def test_plex_stream_forwards_range_header(client, monkeypatch):
    """<audio> elements rely on Range requests to start playback quickly
    and to seek - confirmed this wasn't forwarded at all before."""
    monkeypatch.setattr(radio_api, "plex_client", StubPlexClient())
    route = respx.get("http://plex.test:32400/library/parts/1/1/file.flac").mock(
        return_value=httpx.Response(
            206, content=b"partial", headers={"content-type": "audio/flac", "content-range": "bytes 0-5/100"}
        )
    )

    resp = client.get("/plex/stream/85916", headers={"Range": "bytes=0-5"})

    assert resp.status_code == 206
    assert resp.headers["content-range"] == "bytes 0-5/100"
    assert route.calls.last.request.headers["range"] == "bytes=0-5"


def test_plex_stream_resolve_failure_does_not_leak_token(client, monkeypatch):
    """Regression test: confirmed live on 2026-09-01 - a broken track
    (invalid stream URL) returned the real Plex token in the error body
    to the client (str(exception) included the full failed URL with
    ?X-Plex-Token=... attached)."""
    monkeypatch.setattr(radio_api, "plex_client", StubPlexClient(raise_on={"stream_url"}))

    resp = client.get("/plex/stream/85916")

    assert resp.status_code == 500
    assert "super-secret-token" not in resp.text


@respx.mock
def test_plex_stream_upstream_error_does_not_leak_token(client, monkeypatch):
    monkeypatch.setattr(radio_api, "plex_client", StubPlexClient())
    respx.get("http://plex.test:32400/library/parts/1/1/file.flac").mock(return_value=httpx.Response(404))

    resp = client.get("/plex/stream/85916")

    assert resp.status_code == 502
    assert "super-secret-token" not in resp.text


@respx.mock
def test_plex_art_proxies_image(client, monkeypatch):
    monkeypatch.setattr(radio_api, "plex_client", StubPlexClient())
    respx.get("http://plex.test:32400/library/metadata/1/thumb").mock(
        return_value=httpx.Response(200, content=b"fake-jpeg-bytes", headers={"content-type": "image/jpeg"})
    )

    resp = client.get("/plex/art/85916")

    assert resp.status_code == 200
    assert resp.content == b"fake-jpeg-bytes"
    assert resp.headers["content-type"] == "image/jpeg"


def test_plex_art_missing_returns_404_not_leak_token(client, monkeypatch):
    """Same token-leak class of bug as /plex/stream - checked here too
    since this endpoint has its own separate error handling."""
    monkeypatch.setattr(radio_api, "plex_client", StubPlexClient(raise_on={"art_url"}))

    resp = client.get("/plex/art/85916")

    assert resp.status_code == 404
    assert "super-secret-token" not in resp.text


def test_lastfm_recent_not_configured(client, monkeypatch):
    monkeypatch.setattr(radio_api, "LASTFM_API_KEY", None)
    resp = client.get("/lastfm/recent")
    assert resp.status_code == 400


@respx.mock
def test_lastfm_recent_success(client):
    respx.get("https://ws.audioscrobbler.com/2.0/").mock(
        return_value=httpx.Response(200, json={"recenttracks": {"track": [{"name": "Song"}]}})
    )
    resp = client.get("/lastfm/recent")
    assert resp.status_code == 200
    assert resp.json()["recent_tracks"][0]["name"] == "Song"


@respx.mock
def test_lastfm_top_artists_success(client):
    respx.get("https://ws.audioscrobbler.com/2.0/").mock(
        return_value=httpx.Response(200, json={"topartists": {"artist": [{"name": "Artist"}]}})
    )
    resp = client.get("/lastfm/top-artists")
    assert resp.status_code == 200
    assert resp.json()["top_artists"][0]["name"] == "Artist"


# --- Scrobbling: signing, auth handshake, now-playing/scrobble ---------------

def test_lastfm_sign_matches_lastfm_spec():
    """Last.fm's signing scheme: sort params by key, concatenate key+value
    with no separator, append the secret, MD5. Verified against a
    hand-computed example rather than just re-deriving the same formula
    the implementation uses."""
    import hashlib
    radio_api.LASTFM_API_SECRET = "shhh"
    try:
        sig = radio_api._lastfm_sign({"method": "auth.getToken", "api_key": "abc"})
        expected = hashlib.md5(b"api_keyabcmethodauth.getTokenshhh").hexdigest()
        assert sig == expected
    finally:
        radio_api.LASTFM_API_SECRET = None


def test_lastfm_auth_start_not_configured(client, monkeypatch):
    monkeypatch.setattr(radio_api, "LASTFM_API_SECRET", None)
    resp = client.get("/lastfm/auth/start")
    assert resp.status_code == 400


@respx.mock
def test_lastfm_auth_start_success(client, monkeypatch):
    monkeypatch.setattr(radio_api, "LASTFM_API_SECRET", "shhh")
    respx.get("https://ws.audioscrobbler.com/2.0/").mock(
        return_value=httpx.Response(200, json={"token": "sometoken"})
    )

    resp = client.get("/lastfm/auth/start")

    assert resp.status_code == 200
    body = resp.json()
    assert body["token"] == "sometoken"
    assert "sometoken" in body["auth_url"]
    assert "last.fm/api/auth" in body["auth_url"]


@respx.mock
def test_lastfm_auth_complete_returns_session_key(client, monkeypatch):
    monkeypatch.setattr(radio_api, "LASTFM_API_SECRET", "shhh")
    respx.get("https://ws.audioscrobbler.com/2.0/").mock(
        return_value=httpx.Response(200, json={"session": {"key": "the-session-key", "name": "user"}})
    )

    resp = client.get("/lastfm/auth/complete", params={"token": "sometoken"})

    assert resp.status_code == 200
    assert resp.json()["session_key"] == "the-session-key"


def test_lastfm_now_playing_not_configured(client, monkeypatch):
    monkeypatch.setattr(radio_api, "LASTFM_SESSION_KEY", None)
    resp = client.post("/lastfm/now-playing", params={"artist": "A", "track": "T"})
    assert resp.status_code == 400


@respx.mock
def test_lastfm_now_playing_success(client, monkeypatch):
    monkeypatch.setattr(radio_api, "LASTFM_API_SECRET", "shhh")
    monkeypatch.setattr(radio_api, "LASTFM_SESSION_KEY", "sk123")
    route = respx.post("https://ws.audioscrobbler.com/2.0/").mock(return_value=httpx.Response(200, json={}))

    resp = client.post("/lastfm/now-playing", params={"artist": "Miles Kane", "track": "Troubled Son"})

    assert resp.status_code == 200
    sent = route.calls.last.request.read().decode()
    assert "Miles+Kane" in sent or "Miles%20Kane" in sent


@respx.mock
def test_lastfm_scrobble_success(client, monkeypatch):
    monkeypatch.setattr(radio_api, "LASTFM_API_SECRET", "shhh")
    monkeypatch.setattr(radio_api, "LASTFM_SESSION_KEY", "sk123")
    respx.post("https://ws.audioscrobbler.com/2.0/").mock(return_value=httpx.Response(200, json={}))

    resp = client.post(
        "/lastfm/scrobble",
        params={"artist": "Miles Kane", "track": "Troubled Son", "timestamp": 1788200000}
    )

    assert resp.status_code == 200


@respx.mock
def test_lastfm_scrobble_surfaces_lastfm_error(client, monkeypatch):
    monkeypatch.setattr(radio_api, "LASTFM_API_SECRET", "shhh")
    monkeypatch.setattr(radio_api, "LASTFM_SESSION_KEY", "sk123")
    respx.post("https://ws.audioscrobbler.com/2.0/").mock(
        return_value=httpx.Response(200, json={"error": 9, "message": "Invalid session key"})
    )

    resp = client.post(
        "/lastfm/scrobble",
        params={"artist": "A", "track": "T", "timestamp": 1788200000}
    )

    assert resp.status_code == 502
    assert "Invalid session key" in resp.json()["detail"]
