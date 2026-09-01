"""
PlexClient unit tests, exercised directly against a mocked httpx transport
(not through the FastAPI app) since these hit Plex's XML API shape.
"""
import httpx
import pytest
import respx

from plex_client import PlexClient

PLEX_URL = "http://plex.test:32400"


@pytest.fixture
def plex():
    return PlexClient(url=PLEX_URL, token="fake-token")


LIBRARIES_XML = """<?xml version="1.0" encoding="UTF-8"?>
<MediaContainer size="2">
    <Directory key="1" type="artist" title="Music"/>
    <Directory key="2" type="movie" title="Movies"/>
</MediaContainer>
"""

# Plex's "/library/sections/{key}/all" flattens results: each Track is a
# direct child of the container, with parentTitle=album and
# grandparentTitle=artist as attributes - it does NOT nest Track under a
# Directory/parent element.
TRACKS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<MediaContainer size="1">
    <Track ratingKey="123" key="/library/metadata/123" title="Song One"
           parentTitle="Album One" grandparentTitle="Artist One" duration="215000"/>
</MediaContainer>
"""


@respx.mock
async def test_get_libraries_filters_to_music(plex):
    respx.get(f"{PLEX_URL}/library/sections").mock(
        return_value=httpx.Response(200, content=LIBRARIES_XML, headers={"content-type": "application/xml"})
    )

    libraries = await plex.get_libraries()

    assert len(libraries) == 1
    assert libraries[0]["title"] == "Music"
    assert libraries[0]["type"] == "music"


@respx.mock
async def test_get_library_tracks_extracts_artist_and_album(plex):
    """
    Regression test: get_library_tracks() used to look up each track's
    artist/album via track_elem.findall(".."), which stdlib ElementTree
    doesn't support (no parent pointers) and always returned nothing -
    artist/album were silently always "Unknown".
    """
    respx.get(f"{PLEX_URL}/library/sections/1/all").mock(
        return_value=httpx.Response(200, content=TRACKS_XML, headers={"content-type": "application/xml"})
    )

    tracks = await plex.get_library_tracks("1")

    assert len(tracks) == 1
    track = tracks[0]
    assert track["title"] == "Song One"
    assert track["artist"] == "Artist One"
    assert track["album"] == "Album One"
    assert track["duration"] == 215  # ms -> s
    assert track["rating_key"] == "123"
    # Regression: stream_url used to be absent entirely, so nothing
    # returned by /stream/session was ever actually playable.
    assert track["stream_url"] == "/plex/stream/123"


@respx.mock
async def test_get_library_tracks_falls_back_to_unknown_when_missing(plex):
    xml = """<?xml version="1.0"?>
    <MediaContainer><Track ratingKey="1" key="/x" title="No Metadata" duration="1000"/></MediaContainer>
    """
    respx.get(f"{PLEX_URL}/library/sections/1/all").mock(
        return_value=httpx.Response(200, content=xml, headers={"content-type": "application/xml"})
    )

    tracks = await plex.get_library_tracks("1")

    assert tracks[0]["artist"] == "Unknown"
    assert tracks[0]["album"] == "Unknown"


SEARCH_XML = """<?xml version="1.0" encoding="UTF-8"?>
<MediaContainer size="1">
    <Track ratingKey="456" key="/library/metadata/456" title="Song Two"
           parentTitle="Album Two" grandparentTitle="Artist Two" duration="180000"/>
</MediaContainer>
"""


@respx.mock
async def test_search_tracks_extracts_artist_and_album(plex):
    """
    Regression test: search_tracks() had artist/album swapped
    (parentTitle read as artist, grandparentTitle as album) - the
    opposite of Plex's actual convention, and the opposite of what
    get_library_tracks does two methods above.
    """
    respx.get(f"{PLEX_URL}/search").mock(
        return_value=httpx.Response(200, content=SEARCH_XML, headers={"content-type": "application/xml"})
    )

    tracks = await plex.search_tracks("song two")

    assert tracks[0]["artist"] == "Artist Two"
    assert tracks[0]["album"] == "Album Two"
    assert tracks[0]["stream_url"] == "/plex/stream/456"


def test_requests_xml_not_json(plex):
    """
    Regression test: every method here parses the response with
    ElementTree, but _get_headers() used to send Accept: application/json.
    Plex honors that and returns JSON instead of XML, which breaks
    ET.fromstring() with a cryptic "not well-formed (invalid token)"
    error - confirmed live on 2026-09-01. Accept must ask for XML.
    """
    assert plex._get_headers()["Accept"] == "application/xml"


def test_client_requires_token(monkeypatch):
    monkeypatch.delenv("PLEX_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="PLEX_TOKEN"):
        PlexClient(url=PLEX_URL, token=None)
