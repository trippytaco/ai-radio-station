"""
AI Radio Station Backend - Complete Integration
Includes: Plex streaming, TTS, News, Host generation, Queue management
"""

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import httpx
import hashlib
import json
from collections import OrderedDict
from datetime import datetime
from typing import Optional
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AI Radio Station")

# Allow the frontend dashboard (served from a different origin/host than
# this API, e.g. a browser on the LAN hitting the NAS) to call these
# endpoints. Personal single-user home service, so "*" is fine; tighten
# via ALLOWED_ORIGINS if this is ever exposed beyond the LAN/Tailscale.
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import our new modules
from tts_service import get_tts_provider, set_provider as set_tts_provider
from plex_client import get_plex_client
from news_service import get_news_service
from radio_queue import RadioQueue, SessionBuilder

# Configuration
PLEX_URL = os.getenv("PLEX_URL", "http://localhost:32400")
PLEX_TOKEN = os.getenv("PLEX_TOKEN")
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")
LASTFM_USERNAME = os.getenv("LASTFM_USERNAME")
# Only needed for scrobbling (a write operation) - reading recent
# tracks/top artists works with just LASTFM_API_KEY above. Get the secret
# from the same place as the API key (last.fm/api/account/create).
# LASTFM_SESSION_KEY comes from the one-time /lastfm/auth/* handshake
# below (see README) - it doesn't expire, but there's nowhere to persist
# it in this deploy, so it has to live in the env like every other
# credential here.
LASTFM_API_SECRET = os.getenv("LASTFM_API_SECRET")
LASTFM_SESSION_KEY = os.getenv("LASTFM_SESSION_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "google")

# Host personality profiles
HOST_PROFILES = {
    "alex": {
        "name": "Alex",
        "personality": "sassy, witty, makes pop culture references, calls you out playfully",
        "voice_type": "upbeat, slightly irreverent",
        "tts_voice_id": "alex_female"
    },
    "jordan": {
        "name": "Jordan", 
        "personality": "smooth, laid-back, sardonic humor, insider vibe",
        "voice_type": "conversational, relaxed",
        "tts_voice_id": "jordan_male"
    }
}

# Store user preferences
user_config = {
    "music_weight": 0.5,
    "news_weight": 0.3,
    "ad_weight": 0.1,
    "host_personality": "alex",
    "news_sources": ["bbc", "guardian", "cnn"],
    "context": "commute",
    "active_hosts": ["alex"],
    "tts_provider": TTS_PROVIDER,
    "topics": [],
    "safe_mode": False
}

# Generated host-segment audio, keyed by a UUID handed out in the
# /generate/host-segment response as audio_url. In-memory only (fine for a
# single-instance personal deploy) - bounded FIFO so a long-running
# session doesn't grow this unbounded.
_AUDIO_CACHE_MAX = 50
_audio_cache: "OrderedDict[str, bytes]" = OrderedDict()


def _cache_audio(audio_bytes: bytes) -> str:
    segment_id = uuid.uuid4().hex
    _audio_cache[segment_id] = audio_bytes
    while len(_audio_cache) > _AUDIO_CACHE_MAX:
        _audio_cache.popitem(last=False)
    return segment_id

# Global services
plex_client = None
news_service = None
radio_queue = None

try:
    plex_client = get_plex_client()
except Exception as e:
    print(f"Warning: Plex client not available: {e}")

try:
    news_service = get_news_service()
except Exception as e:
    print(f"Warning: News service not available: {e}")

radio_queue = RadioQueue()


@app.on_event("startup")
async def startup():
    """Initialize services on startup"""
    global plex_client, news_service, radio_queue
    try:
        if not plex_client:
            plex_client = get_plex_client()
        print("✓ Plex client initialized")
    except Exception as e:
        print(f"✗ Plex client initialization failed: {e}")
    
    try:
        if not news_service:
            news_service = get_news_service()
        print("✓ News service initialized")
    except Exception as e:
        print(f"✗ News service initialization failed: {e}")
    
    print("✓ API startup complete")


# ============================================================================
# HEALTH & STATUS
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "ai-radio-station",
        "tts_provider": TTS_PROVIDER,
        "timestamp": datetime.now().isoformat()
    }


# ============================================================================
# CONFIGURATION
# ============================================================================

@app.get("/config")
async def get_config():
    """Get current radio station configuration"""
    return user_config


@app.post("/config")
async def update_config(new_config: dict):
    """Update radio station configuration"""
    global user_config
    user_config.update(new_config)
    
    # Update radio queue weights
    radio_queue.update_weights(
        user_config["music_weight"],
        user_config["news_weight"],
        user_config["ad_weight"]
    )
    
    return {"status": "updated", "config": user_config}


# ============================================================================
# PLEX INTEGRATION
# ============================================================================

@app.get("/plex/libraries")
async def get_plex_libraries():
    """Get available Plex music libraries"""
    if not plex_client:
        raise HTTPException(status_code=500, detail="Plex client not available")
    
    try:
        libraries = await plex_client.get_libraries()
        return {"status": "success", "libraries": libraries}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Plex error: {str(e)}")


@app.get("/plex/tracks")
async def get_plex_tracks(library_key: str = "1", limit: int = 50):
    """Get tracks from Plex library"""
    if not plex_client:
        raise HTTPException(status_code=500, detail="Plex client not available")
    
    try:
        tracks = await plex_client.get_library_tracks(library_key, limit)
        return {"status": "success", "tracks": tracks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Plex error: {str(e)}")


@app.get("/plex/stream/{rating_key}")
async def stream_plex_track(rating_key: str, request: Request):
    """
    Proxy-stream a track from Plex. Tracks here are lossless FLAC and can
    run 40-50MB+, so this genuinely streams (chunk by chunk, no full
    in-memory buffering) and forwards Range requests - without Range
    support, <audio> playback has to wait for the entire file to download
    before it can start, and can't seek.
    """
    if not plex_client:
        raise HTTPException(status_code=500, detail="Plex client not available")

    try:
        stream_url = await plex_client.get_track_stream_url(rating_key)
    except Exception as e:
        # Deliberately not including str(e) here - it can contain the
        # upstream URL with the Plex token embedded as a query param
        # (confirmed live: an earlier version of this leaked the real
        # token to any client that hit a broken track).
        print(f"Plex stream resolve error for {rating_key}: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="Could not resolve this track on Plex")

    client = httpx.AsyncClient()
    forward_headers = {}
    if request.headers.get("range"):
        forward_headers["Range"] = request.headers["range"]

    try:
        req = client.build_request("GET", stream_url, headers=forward_headers)
        upstream = await client.send(req, stream=True)
    except Exception as e:
        await client.aclose()
        print(f"Plex stream fetch error for {rating_key}: {type(e).__name__}: {e}")
        raise HTTPException(status_code=502, detail="Could not reach Plex for this track")

    if upstream.status_code >= 400:
        await upstream.aclose()
        await client.aclose()
        raise HTTPException(status_code=502, detail=f"Plex returned {upstream.status_code} for this track")

    async def body():
        try:
            async for chunk in upstream.aiter_bytes():
                yield chunk
        finally:
            await upstream.aclose()
            await client.aclose()

    passthrough_headers = {}
    for h in ("content-length", "content-range", "accept-ranges"):
        if h in upstream.headers:
            passthrough_headers[h] = upstream.headers[h]
    passthrough_headers.setdefault("accept-ranges", "bytes")

    return StreamingResponse(
        body(),
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type", "audio/mpeg"),
        headers=passthrough_headers
    )


@app.get("/plex/art/{rating_key}")
async def get_plex_art(rating_key: str):
    """Proxy a track's cover art. Images here are small (unlike the FLAC
    streams above), so a plain buffered fetch is fine - no need for the
    streaming/Range machinery /plex/stream needs."""
    if not plex_client:
        raise HTTPException(status_code=500, detail="Plex client not available")

    try:
        art_url = await plex_client.get_track_art_url(rating_key)
    except Exception as e:
        # Same reasoning as /plex/stream: never include str(e) here, it
        # can carry the Plex token embedded in the (failed) upstream URL.
        print(f"Plex art resolve error for {rating_key}: {type(e).__name__}: {e}")
        raise HTTPException(status_code=404, detail="No cover art available for this track")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(art_url, timeout=10.0, follow_redirects=True)
            response.raise_for_status()
            return Response(
                content=response.content,
                media_type=response.headers.get("content-type", "image/jpeg"),
                headers={"Cache-Control": "public, max-age=86400"}
            )
    except Exception as e:
        print(f"Plex art fetch error for {rating_key}: {type(e).__name__}: {e}")
        raise HTTPException(status_code=502, detail="Could not reach Plex for this track's art")


# ============================================================================
# LAST.FM INTEGRATION
# ============================================================================

@app.get("/lastfm/recent")
async def get_lastfm_recent(limit: int = 50):
    """Fetch recent tracks from Last.fm"""
    if not LASTFM_API_KEY or not LASTFM_USERNAME:
        raise HTTPException(status_code=400, detail="Last.fm credentials not configured")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://ws.audioscrobbler.com/2.0/",
                params={
                    "method": "user.getrecenttracks",
                    "user": LASTFM_USERNAME,
                    "api_key": LASTFM_API_KEY,
                    "limit": limit,
                    "format": "json"
                }
            )
            data = response.json()
            return {
                "status": "success",
                "recent_tracks": data.get("recenttracks", {}).get("track", [])
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Last.fm error: {str(e)}")


@app.get("/lastfm/top-artists")
async def get_lastfm_top_artists(period: str = "7day", limit: int = 20):
    """Get user's top artists from Last.fm"""
    if not LASTFM_API_KEY or not LASTFM_USERNAME:
        raise HTTPException(status_code=400, detail="Last.fm credentials not configured")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://ws.audioscrobbler.com/2.0/",
                params={
                    "method": "user.gettopartists",
                    "user": LASTFM_USERNAME,
                    "period": period,
                    "api_key": LASTFM_API_KEY,
                    "limit": limit,
                    "format": "json"
                }
            )
            data = response.json()
            return {
                "status": "success",
                "top_artists": data.get("topartists", {}).get("artist", [])
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Last.fm error: {str(e)}")


def _lastfm_sign(params: dict) -> str:
    """
    Last.fm's request-signing scheme: sort params by key, concatenate
    key+value pairs with no separator, append the shared secret, MD5 the
    result. Required for every authenticated (write) call - scrobble,
    updateNowPlaying, and the auth handshake itself.
    """
    sig_string = "".join(f"{k}{v}" for k, v in sorted(params.items())) + LASTFM_API_SECRET
    return hashlib.md5(sig_string.encode("utf-8")).hexdigest()


async def _lastfm_signed_call(method: str, params: dict, http_method: str = "POST") -> dict:
    if not LASTFM_API_KEY or not LASTFM_API_SECRET:
        raise HTTPException(status_code=400, detail="LASTFM_API_KEY/LASTFM_API_SECRET not configured")

    call_params = {**params, "method": method, "api_key": LASTFM_API_KEY}
    call_params["api_sig"] = _lastfm_sign(call_params)
    call_params["format"] = "json"

    async with httpx.AsyncClient() as client:
        if http_method == "POST":
            response = await client.post("https://ws.audioscrobbler.com/2.0/", data=call_params, timeout=10.0)
        else:
            response = await client.get("https://ws.audioscrobbler.com/2.0/", params=call_params, timeout=10.0)

    data = response.json()
    if "error" in data:
        # Never log call_params here - api_sig alone is a signed
        # credential-equivalent, and a scrobble call's params include
        # the session key.
        raise HTTPException(status_code=502, detail=f"Last.fm error {data['error']}: {data.get('message', '')}")
    return data


@app.get("/lastfm/auth/start")
async def lastfm_auth_start():
    """
    Step 1 of the one-time scrobbling setup. Returns a Last.fm URL to
    open and approve, plus the token /lastfm/auth/complete needs next.
    Only needed once - the resulting session key doesn't expire. See the
    README for the full walkthrough.
    """
    if not LASTFM_API_KEY or not LASTFM_API_SECRET:
        raise HTTPException(status_code=400, detail="LASTFM_API_KEY/LASTFM_API_SECRET not configured")

    data = await _lastfm_signed_call("auth.getToken", {}, http_method="GET")
    token = data.get("token")
    if not token:
        raise HTTPException(status_code=502, detail="Last.fm did not return a token")

    return {
        "token": token,
        "auth_url": f"https://www.last.fm/api/auth/?api_key={LASTFM_API_KEY}&token={token}",
        "next_step": "Open auth_url, click Allow, then call GET /lastfm/auth/complete?token=<this token>"
    }


@app.get("/lastfm/auth/complete")
async def lastfm_auth_complete(token: str):
    """
    Step 2: exchanges an approved token for a permanent session key. This
    key has to be saved as LASTFM_SESSION_KEY (e.g. in Portainer) for
    scrobbling to work - there's nowhere to persist it in this deploy, so
    it isn't stored automatically. Comes back once in this response and
    is never logged.
    """
    data = await _lastfm_signed_call("auth.getSession", {"token": token}, http_method="GET")
    session_key = data.get("session", {}).get("key")
    if not session_key:
        raise HTTPException(status_code=502, detail="Last.fm did not return a session key")

    return {
        "session_key": session_key,
        "next_step": "Save this as LASTFM_SESSION_KEY and redeploy - it won't be shown again from here."
    }


@app.post("/lastfm/now-playing")
async def lastfm_now_playing(artist: str, track: str, album: Optional[str] = None):
    """Updates Last.fm's live 'now playing' status. Best-effort - failures
    here shouldn't interrupt playback, so the frontend should ignore
    errors from this endpoint rather than surface them."""
    if not LASTFM_SESSION_KEY:
        raise HTTPException(status_code=400, detail="LASTFM_SESSION_KEY not configured")

    params = {"artist": artist, "track": track, "sk": LASTFM_SESSION_KEY}
    if album:
        params["album"] = album
    await _lastfm_signed_call("track.updateNowPlaying", params)
    return {"status": "ok"}


@app.post("/lastfm/scrobble")
async def lastfm_scrobble(artist: str, track: str, timestamp: int, album: Optional[str] = None):
    """
    Scrobbles a track. Per Last.fm's own rules a scrobble should only be
    submitted for a track that's actually played through - the frontend
    calls this on natural end-of-track, not on skip. `timestamp` is the
    unix time (seconds) the track STARTED playing, not when it finished.
    """
    if not LASTFM_SESSION_KEY:
        raise HTTPException(status_code=400, detail="LASTFM_SESSION_KEY not configured")

    params = {
        "artist": artist, "track": track, "timestamp": timestamp, "sk": LASTFM_SESSION_KEY
    }
    if album:
        params["album"] = album
    await _lastfm_signed_call("track.scrobble", params)
    return {"status": "ok"}


# ============================================================================
# NEWS INTEGRATION
# ============================================================================

@app.get("/news/headlines")
async def get_news_headlines(source: str = None, limit: int = 5):
    """Get news headlines. When no specific source is requested, only
    sources enabled in user_config["news_sources"] are queried."""
    if not news_service:
        raise HTTPException(status_code=500, detail="News service not available")

    try:
        headlines = await news_service.get_headlines(
            source, limit, enabled_sources=user_config.get("news_sources")
        )
        return {"status": "success", "headlines": headlines}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"News error: {str(e)}")


# ============================================================================
# HOST SEGMENT GENERATION
# ============================================================================

@app.post("/generate/host-segment")
async def generate_host_segment(
    context: Optional[str] = None,
    topic: Optional[str] = None,
):
    """Generate AI host banter/commentary segment with TTS"""
    
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")
    
    host = HOST_PROFILES.get(user_config["host_personality"], HOST_PROFILES["alex"])

    safety_note = (
        "\n        Keep it family-friendly: no profanity, no explicit or "
        "controversial content."
        if user_config.get("safe_mode") else ""
    )
    topics = user_config.get("topics") or []
    topics_note = (
        f"\n        The listener is especially interested in: {', '.join(topics)} - "
        "lean into that when it's a natural fit, don't force it."
        if topics else ""
    )

    if context == "motivation":
        prompt = f"""You are {host['name']}, a {host['personality']} radio host. 
        Generate a 30-second motivational snippet for someone on a run. 
        Be encouraging but not syrupy. Make it personal—acknowledge this is THEIR radio station.
        Keep it punchy and energetic.
        {safety_note}{topics_note}
        Return ONLY the spoken text, no stage directions."""
    
    elif context == "news_banter":
        prompt = f"""You are {host['name']}, a {host['personality']} radio host.
        You're about to discuss this news topic: {topic}
        Generate a witty 20-second intro to the news segment that hooks the listener.
        Make it edgy and modern. Be sarcastic if appropriate.
        {safety_note}{topics_note}
        Return ONLY the spoken text, no stage directions."""
    
    elif context == "ad_lib":
        category_hint = f"\n        The product should be in the general category of: {topic}." if topic else ""
        prompt = f"""You are {host['name']}, a {host['personality']} radio host.
        Generate a hilarious 30-second fake ad read for a completely fictional product.
        Make it absurd and funny. Commit fully to the bit. Invent a fresh,
        specific product and brand name - don't reuse a generic/placeholder
        one like "ExistencePro".{category_hint}
        {safety_note}{topics_note}
        Return ONLY the spoken text, no stage directions."""
    
    elif context == "transition":
        prompt = f"""You are {host['name']}, a {host['personality']} radio host.
        Generate a smooth 10-second transition between songs for THIS LISTENER's personal station.
        Acknowledge them directly, be clever, maybe reference the song that just played.
        {safety_note}{topics_note}
        Return ONLY the spoken text, no stage directions."""
    
    else:
        prompt = f"""You are {host['name']}, a {host['personality']} radio host.
        Generate a 20-second segment of natural, engaging host banter.
        Imagine you're talking to ONE listener—this is their personal station.
        {safety_note}{topics_note}
        Return ONLY the spoken text, no stage directions."""
    
    try:
        # Get text from Claude
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-sonnet-5",
                    "max_tokens": 200,
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                error_text = response.text
                print(f"ERROR: Anthropic API returned {response.status_code}: {error_text}")
                raise HTTPException(status_code=500, detail=f"Claude API error: {response.status_code}")
            
            data = response.json()
            
            if not data.get("content") or len(data["content"]) == 0:
                print(f"ERROR: No content in response: {data}")
                raise HTTPException(status_code=500, detail="No content in Claude response")
            
            text = data["content"][0].get("text", "Coming up next...")
        
        # Generate TTS audio
        audio_url = None
        try:
            tts_provider = get_tts_provider()
            audio_bytes = await tts_provider.synthesize(text, host["tts_voice_id"])
            if audio_bytes:
                audio_url = f"/audio/segment/{_cache_audio(audio_bytes)}"
        except Exception as tts_error:
            print(f"TTS error: {str(tts_error)}, returning text-only response")

        return {
            "host": host["name"],
            "context": context,
            "text": text,
            "timestamp": datetime.now().isoformat(),
            "audio_available": audio_url is not None,
            "audio_url": audio_url,
            "tts_provider": TTS_PROVIDER if audio_url else None
        }
    
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Generation error: {type(e).__name__}: {str(e)}"
        print(f"ERROR: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)


# ============================================================================
# AUDIO ENDPOINTS
# ============================================================================

@app.get("/audio/segment/{segment_id}")
async def get_segment_audio(segment_id: str):
    """Serve previously-generated host-segment audio, cached in memory by
    /generate/host-segment (see audio_url in its response)."""
    audio_bytes = _audio_cache.get(segment_id)
    if audio_bytes is None:
        raise HTTPException(status_code=404, detail="Segment audio not found (expired or never existed)")
    return Response(content=audio_bytes, media_type="audio/mpeg")


@app.get("/stream/session")
async def stream_radio_session(duration_minutes: int = 60):
    """Stream a complete radio session"""
    
    async def generate():
        # Build session
        builder = SessionBuilder(duration_minutes)
        
        # Get music tracks
        music_tracks = []
        if plex_client:
            try:
                music_tracks = await plex_client.get_library_tracks("1", limit=100)
            except:
                pass
        
        # Build segments
        segments = await builder.build(
            music_tracks=music_tracks,
            host_generator=generate_host_segment,
            news_service=news_service,
            host_personality=user_config["host_personality"],
            news_sources=user_config.get("news_sources")
        )
        
        # Stream as NDJSON
        for segment in segments:
            yield json.dumps({
                "type": segment.type,
                "duration": segment.duration_seconds,
                "content": segment.content,
                "host": segment.host,
                "generated_at": segment.generated_at
            }).encode() + b"\n"
    
    return StreamingResponse(generate(), media_type="application/x-ndjson")


# ============================================================================
# TTS PROVIDER MANAGEMENT
# ============================================================================

@app.get("/tts/providers")
async def list_tts_providers():
    """List available TTS providers"""
    return {
        "current": TTS_PROVIDER,
        "available": ["google", "elevenlabs"],
        "hosts": {
            "alex": HOST_PROFILES["alex"]["tts_voice_id"],
            "jordan": HOST_PROFILES["jordan"]["tts_voice_id"]
        }
    }


@app.post("/tts/switch")
async def switch_tts_provider(provider: str):
    """Switch between TTS providers"""
    if provider not in ["google", "elevenlabs"]:
        raise HTTPException(status_code=400, detail="Invalid TTS provider")

    global user_config, TTS_PROVIDER
    try:
        set_tts_provider(provider)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to switch TTS provider: {str(e)}")

    user_config["tts_provider"] = provider
    TTS_PROVIDER = provider

    return {"status": "switched", "provider": provider}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
