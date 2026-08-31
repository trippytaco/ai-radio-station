"""
News Service
Fetch headlines from multiple sources
"""

import asyncio
import os
from typing import List, Dict, Any, Optional
import httpx


def _redact_url(url: httpx.URL) -> str:
    """Scheme/host/path only - strips query params (api-key/apiKey are
    passed as query params by every source below, and would otherwise
    leak into logs verbatim via str(exception))."""
    try:
        return f"{url.scheme}://{url.host}{url.path}"
    except Exception:
        return "<upstream>"


def _log_source_error(source_name: str, e: Exception) -> None:
    if isinstance(e, httpx.HTTPStatusError):
        print(f"{source_name} error: HTTP {e.response.status_code} from {_redact_url(e.request.url)}")
    elif isinstance(e, httpx.RequestError):
        print(f"{source_name} error: {type(e).__name__} contacting {_redact_url(e.request.url)}")
    else:
        print(f"{source_name} error: {type(e).__name__}: {e}")


class NewsSource:
    """Base class for news sources"""
    
    async def get_headlines(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get headlines from this source"""
        raise NotImplementedError


class BBCNews(NewsSource):
    """BBC News source"""
    
    async def get_headlines(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Fetch BBC news headlines"""
        try:
            async with httpx.AsyncClient() as client:
                # Using NewsAPI for BBC
                api_key = os.getenv("NEWSAPI_KEY")
                if not api_key:
                    return []
                
                response = await client.get(
                    "https://newsapi.org/v2/top-headlines",
                    params={
                        "sources": "bbc-news",
                        "sortBy": "publishedAt",
                        "apiKey": api_key,
                        "pageSize": limit
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                
                data = response.json()
                headlines = []
                
                for article in data.get("articles", []):
                    headlines.append({
                        "title": article.get("title"),
                        "description": article.get("description"),
                        "source": "BBC News",
                        "url": article.get("url"),
                        "published_at": article.get("publishedAt")
                    })
                
                return headlines[:limit]
        
        except Exception as e:
            _log_source_error("BBC News", e)
            return []


class GuardianNews(NewsSource):
    """The Guardian news source"""
    
    async def get_headlines(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Fetch Guardian headlines"""
        try:
            api_key = os.getenv("GUARDIAN_API_KEY")
            if not api_key:
                return []
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://content.guardianapis.com/search",
                    params={
                        "api-key": api_key,
                        "show-fields": "trailText,thumbnail",
                        "page-size": limit,
                        "order-by": "newest"
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                
                data = response.json()
                headlines = []
                
                for result in data.get("response", {}).get("results", []):
                    headlines.append({
                        "title": result.get("webTitle"),
                        "description": result.get("fields", {}).get("trailText"),
                        "source": "The Guardian",
                        "url": result.get("webUrl"),
                        "published_at": result.get("webPublicationDate")
                    })
                
                return headlines[:limit]
        
        except Exception as e:
            _log_source_error("Guardian News", e)
            return []


class CNNNews(NewsSource):
    """CNN news source"""
    
    async def get_headlines(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Fetch CNN headlines"""
        try:
            async with httpx.AsyncClient() as client:
                api_key = os.getenv("NEWSAPI_KEY")
                if not api_key:
                    return []
                
                response = await client.get(
                    "https://newsapi.org/v2/top-headlines",
                    params={
                        "sources": "cnn",
                        "sortBy": "publishedAt",
                        "apiKey": api_key,
                        "pageSize": limit
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                
                data = response.json()
                headlines = []
                
                for article in data.get("articles", []):
                    headlines.append({
                        "title": article.get("title"),
                        "description": article.get("description"),
                        "source": "CNN",
                        "url": article.get("url"),
                        "published_at": article.get("publishedAt")
                    })
                
                return headlines[:limit]
        
        except Exception as e:
            _log_source_error("CNN News", e)
            return []


class NewsService:
    """Aggregated news service"""
    
    def __init__(self):
        self.sources = {
            "bbc": BBCNews(),
            "guardian": GuardianNews(),
            "cnn": CNNNews()
        }
    
    async def get_headlines(self, source: str = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Get headlines from specified source or all sources"""
        if source and source in self.sources:
            return await self.sources[source].get_headlines(limit)
        
        # Get from all sources concurrently
        results = await asyncio.gather(
            *(src.get_headlines(limit) for src in self.sources.values())
        )
        all_headlines = [h for headlines in results for h in headlines]
        
        # Sort by date
        all_headlines.sort(
            key=lambda x: x.get("published_at", ""),
            reverse=True
        )
        
        return all_headlines[:limit]
    
    async def get_random_headline(self) -> Optional[Dict[str, Any]]:
        """Get a random headline"""
        try:
            headlines = await self.get_headlines(limit=10)
            import random
            return random.choice(headlines) if headlines else None
        except Exception as e:
            print(f"Error getting random headline: {str(e)}")
            return None


# Global instance
_news_service: Optional[NewsService] = None


def get_news_service() -> NewsService:
    """Get or create global news service"""
    global _news_service
    if _news_service is None:
        _news_service = NewsService()
    return _news_service
