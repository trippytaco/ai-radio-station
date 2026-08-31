"""
Plex Media Server Integration
Fetch music library and stream audio
"""

import os
from typing import List, Optional, Dict, Any
import httpx
from xml.etree import ElementTree as ET


class PlexClient:
    """Client for interacting with Plex Media Server"""
    
    def __init__(self, url: str = None, token: str = None):
        self.url = url or os.getenv("PLEX_URL", "http://localhost:32400")
        self.token = token or os.getenv("PLEX_TOKEN")
        
        if not self.token:
            raise RuntimeError("PLEX_TOKEN not configured")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Plex API requests"""
        return {
            "X-Plex-Token": self.token,
            "Accept": "application/json"
        }
    
    async def get_libraries(self) -> List[Dict[str, Any]]:
        """Get available music libraries"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.url}/library/sections",
                    headers=self._get_headers(),
                    timeout=10.0
                )
                response.raise_for_status()
                
                # Parse XML response
                root = ET.fromstring(response.content)
                libraries = []
                
                for dir_elem in root.findall("Directory"):
                    if dir_elem.get("type") == "artist":  # Music library
                        libraries.append({
                            "key": dir_elem.get("key"),
                            "title": dir_elem.get("title"),
                            "type": "music"
                        })
                
                return libraries
        
        except Exception as e:
            raise RuntimeError(f"Plex library fetch error: {str(e)}")
    
    async def get_library_tracks(self, library_key: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get tracks from a music library"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.url}/library/sections/{library_key}/all",
                    headers=self._get_headers(),
                    params={"limit": limit},
                    timeout=10.0
                )
                response.raise_for_status()
                
                root = ET.fromstring(response.content)
                tracks = []
                
                for track_elem in root.findall("Track"):
                    # Get parent album/artist info
                    album = None
                    artist = None
                    
                    for parent in track_elem.findall(".."):
                        album = parent.get("title")
                        break
                    
                    tracks.append({
                        "key": track_elem.get("key"),
                        "title": track_elem.get("title"),
                        "artist": artist or "Unknown",
                        "album": album or "Unknown",
                        "duration": int(track_elem.get("duration", 0)) // 1000,  # Convert to seconds
                        "rating_key": track_elem.get("ratingKey")
                    })
                
                return tracks
        
        except Exception as e:
            raise RuntimeError(f"Plex tracks fetch error: {str(e)}")
    
    async def get_track_stream_url(self, rating_key: str) -> str:
        """Get stream URL for a track"""
        return f"{self.url}/library/metadata/{rating_key}/file?X-Plex-Token={self.token}"
    
    async def get_random_track(self, library_key: str) -> Optional[Dict[str, Any]]:
        """Get a random track from library"""
        try:
            tracks = await self.get_library_tracks(library_key, limit=1)
            return tracks[0] if tracks else None
        except Exception as e:
            print(f"Error getting random track: {str(e)}")
            return None
    
    async def search_tracks(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for tracks in Plex"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.url}/search",
                    headers=self._get_headers(),
                    params={
                        "query": query,
                        "sectionID": "1",  # Assuming music is section 1
                        "type": "track",
                        "limit": limit
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                
                root = ET.fromstring(response.content)
                tracks = []
                
                for track_elem in root.findall(".//Track"):
                    tracks.append({
                        "key": track_elem.get("key"),
                        "title": track_elem.get("title"),
                        "artist": track_elem.get("parentTitle", "Unknown"),
                        "album": track_elem.get("grandparentTitle", "Unknown"),
                        "duration": int(track_elem.get("duration", 0)) // 1000,
                        "rating_key": track_elem.get("ratingKey")
                    })
                
                return tracks
        
        except Exception as e:
            raise RuntimeError(f"Plex search error: {str(e)}")


# Global instance
_plex_client: Optional[PlexClient] = None


def get_plex_client() -> PlexClient:
    """Get or create global Plex client"""
    global _plex_client
    if _plex_client is None:
        _plex_client = PlexClient()
    return _plex_client
