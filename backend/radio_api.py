"""
AI Radio Station Backend - Complete Integration
Includes: Plex streaming, TTS, News, Host generation, Queue management
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import httpx
import json
from datetime import datetime
from typing import Optional
import os
from dotenv import load_dotenv
import io

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
    "tts_provider": TTS_PROVIDER
}

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
async def stream_plex_track(rating_key: str):
    """Stream a track from Plex"""
    if not plex_client:
        raise HTTPException(status_code=500, detail="Plex client not available")
    
    try:
        stream_url = await plex_client.get_track_stream_url(rating_key)
        
        # Proxy the stream from Plex
        async with httpx.AsyncClient() as client:
            response = await client.get(stream_url, follow_redirects=True)
            response.raise_for_status()
            
            return StreamingResponse(
                io.BytesIO(response.content),
                media_type="audio/mpeg",
                headers={"Content-Disposition": f"inline; filename=track.mp3"}
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stream error: {str(e)}")


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


# ============================================================================
# NEWS INTEGRATION
# ============================================================================

@app.get("/news/headlines")
async def get_news_headlines(source: str = None, limit: int = 5):
    """Get news headlines"""
    if not news_service:
        raise HTTPException(status_code=500, detail="News service not available")
    
    try:
        headlines = await news_service.get_headlines(source, limit)
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
    
    if context == "motivation":
        prompt = f"""You are {host['name']}, a {host['personality']} radio host. 
        Generate a 30-second motivational snippet for someone on a run. 
        Be encouraging but not syrupy. Make it personal—acknowledge this is THEIR radio station.
        Keep it punchy and energetic.
        Return ONLY the spoken text, no stage directions."""
    
    elif context == "news_banter":
        prompt = f"""You are {host['name']}, a {host['personality']} radio host.
        You're about to discuss this news topic: {topic}
        Generate a witty 20-second intro to the news segment that hooks the listener.
        Make it edgy and modern. Be sarcastic if appropriate.
        Return ONLY the spoken text, no stage directions."""
    
    elif context == "ad_lib":
        prompt = f"""You are {host['name']}, a {host['personality']} radio host.
        Generate a hilarious 30-second fake ad read for a completely fictional product.
        Make it absurd and funny. Commit fully to the bit.
        Example vibe: "Tired of your life? Try NEW ExistencePro™..."
        Return ONLY the spoken text, no stage directions."""
    
    elif context == "transition":
        prompt = f"""You are {host['name']}, a {host['personality']} radio host.
        Generate a smooth 10-second transition between songs for THIS LISTENER's personal station.
        Acknowledge them directly, be clever, maybe reference the song that just played.
        Return ONLY the spoken text, no stage directions."""
    
    else:
        prompt = f"""You are {host['name']}, a {host['personality']} radio host.
        Generate a 20-second segment of natural, engaging host banter.
        Imagine you're talking to ONE listener—this is their personal station.
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
        try:
            tts_provider = get_tts_provider()
            audio_bytes = await tts_provider.synthesize(text, host["tts_voice_id"])
        except Exception as tts_error:
            print(f"TTS error: {str(tts_error)}, returning text-only response")
            audio_bytes = None
        
        return {
            "host": host["name"],
            "context": context,
            "text": text,
            "timestamp": datetime.now().isoformat(),
            "audio_available": audio_bytes is not None,
            "tts_provider": TTS_PROVIDER if audio_bytes else None
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
    """Get pre-generated audio for a segment"""
    # This would be implemented with audio caching/generation
    raise HTTPException(status_code=501, detail="Not yet implemented")


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
            host_personality=user_config["host_personality"]
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
