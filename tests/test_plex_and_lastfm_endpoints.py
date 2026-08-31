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
