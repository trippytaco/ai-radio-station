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
