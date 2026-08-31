"""
Personalized AI Radio Station Backend
Integrates Plex, Last.fm, news sources, and AI host personalities
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import httpx
import json
from datetime import datetime
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AI Radio Station")

# Configuration
PLEX_URL = os.getenv("PLEX_URL", "http://localhost:32400")
PLEX_TOKEN = os.getenv("PLEX_TOKEN")
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")
LASTFM_USERNAME = os.getenv("LASTFM_USERNAME")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Host personality profiles
HOST_PROFILES = {
    "alex": {
        "name": "Alex",
        "personality": "sassy, witty, makes pop culture references, calls you out playfully",
        "voice_type": "upbeat, slightly irreverent"
    },
    "jordan": {
        "name": "Jordan", 
        "personality": "smooth, laid-back, sardonic humor, insider vibe",
        "voice_type": "conversational, relaxed"
    }
}

# Store user preferences
user_config = {
    "music_weight": 0.5,  # 0-1: how much music vs talk
    "news_weight": 0.3,   # 0-1: how much news segments
    "ad_weight": 0.1,     # 0-1: hilarious ads frequency
    "host_personality": "alex",
    "news_sources": ["bbc", "guardian", "cnn"],
    "context": "commute",  # "workout", "commute", "chill"
    "active_hosts": ["alex"]
}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}


@app.get("/config")
async def get_config():
    """Get current radio station configuration"""
    return user_config


@app.post("/config")
async def update_config(new_config: dict):
    """Update radio station configuration"""
    global user_config
    user_config.update(new_config)
    return {"status": "updated", "config": user_config}


@app.get("/plex/library")
async def get_plex_library():
    """Fetch user's music library from Plex"""
    if not PLEX_TOKEN:
        raise HTTPException(status_code=400, detail="Plex token not configured")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{PLEX_URL}/library/sections",
                headers={"X-Plex-Token": PLEX_TOKEN}
            )
            # Parse XML response and extract music libraries
            # (Plex returns XML, so we'd parse it here)
            return {"status": "connected", "libraries": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Plex connection error: {str(e)}")


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
    """Get user's top artists from Last.fm to understand taste"""
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


@app.post("/generate/host-segment")
async def generate_host_segment(
    context: Optional[str] = None,
    topic: Optional[str] = None,
    duration_seconds: int = 60
):
    """
    Generate AI host banter/commentary segment.
    Context can be: "intro", "news_banter", "motivation", "transition", "ad_lib"
    """
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
    
    # Check if API key is configured
    if not ANTHROPIC_API_KEY:
        print("ERROR: ANTHROPIC_API_KEY not set")
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")
    
    try:
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
            
            # Check response status
            if response.status_code != 200:
                error_text = response.text
                print(f"ERROR: Anthropic API returned {response.status_code}: {error_text}")
                raise HTTPException(status_code=500, detail=f"Anthropic API error {response.status_code}: {error_text}")
            
            data = response.json()
            
            # Check if we got content back
            if not data.get("content") or len(data["content"]) == 0:
                print(f"ERROR: No content in response: {data}")
                raise HTTPException(status_code=500, detail="No content in Anthropic response")
            
            text = data["content"][0].get("text", "Coming up next...")
            print(f"SUCCESS: Generated segment - {context}")
            
            return {
                "host": host["name"],
                "context": context,
                "text": text,
                "timestamp": datetime.now().isoformat()
            }
    
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Generation error: {type(e).__name__}: {str(e)}"
        print(f"ERROR: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)


@app.get("/stream")
async def stream_radio(duration_minutes: int = 60):
    """
    Stream personalized radio session.
    Combines music from Plex, host segments, news, and ads.
    Returns a stream of audio metadata and content.
    """
    
    async def generate():
        """Generator that produces radio session content"""
        # This is a simplified version - in reality you'd:
        # 1. Fetch music from Plex
        # 2. Get Last.fm taste profile
        # 3. Generate segments based on time/context
        # 4. Mix in news headlines
        # 5. Generate host transitions
        # 6. Output as stream
        
        session_data = {
            "session_id": datetime.now().isoformat(),
            "config": user_config,
            "segments": [
                {
                    "type": "host_intro",
                    "host": user_config["host_personality"],
                    "text": "Hey! It's your station, let's make this count."
                },
                {
                    "type": "music",
                    "source": "plex",
                    "artist": "Your Top Artist",
                    "track": "Your Favorite Song"
                },
                {
                    "type": "host_transition",
                    "text": "Smooth track. Anyway..."
                },
                {
                    "type": "news",
                    "headline": "Today's headlines incoming",
                    "source": "bbc"
                },
                {
                    "type": "ad_lib",
                    "text": "This segment brought to you by..."
                }
            ]
        }
        
        # Yield as NDJSON (newline-delimited JSON)
        for segment in session_data["segments"]:
            yield json.dumps(segment).encode() + b"\n"
    
    return StreamingResponse(generate(), media_type="application/x-ndjson")


@app.post("/schedule")
async def set_schedule(schedule: dict):
    """Set time-based schedule for content types"""
    # Example: {"06:00": "workout", "09:00": "commute", "12:00": "chill"}
    return {"status": "scheduled", "schedule": schedule}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
