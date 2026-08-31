"""NewsService unit tests."""
import httpx
import pytest
import respx

from news_service import NewsService


@pytest.fixture
def news(monkeypatch):
    monkeypatch.setenv("NEWSAPI_KEY", "fake-newsapi-key")
    monkeypatch.setenv("GUARDIAN_API_KEY", "fake-guardian-key")
    return NewsService()


@respx.mock
async def test_get_headlines_single_source(news):
    respx.get("https://newsapi.org/v2/top-headlines").mock(
        return_value=httpx.Response(200, json={"articles": [
            {"title": "BBC headline", "description": "d", "url": "https://bbc.test/1", "publishedAt": "2026-08-31T00:00:00Z"},
        ]})
    )

    headlines = await news.get_headlines(source="bbc", limit=5)

    assert len(headlines) == 1
    assert headlines[0]["source"] == "BBC News"
    assert headlines[0]["title"] == "BBC headline"


@respx.mock
async def test_get_headlines_all_sources_are_merged_and_sorted(news):
    respx.get("https://newsapi.org/v2/top-headlines").mock(
        return_value=httpx.Response(200, json={"articles": [
            {"title": "Older", "description": "d", "url": "u", "publishedAt": "2026-08-30T00:00:00Z"},
        ]})
    )
    respx.get("https://open-platform.theguardian.com/search").mock(
        return_value=httpx.Response(200, json={"response": {"results": [
            {"webTitle": "Newer", "fields": {"trailText": "d"}, "webUrl": "u", "webPublicationDate": "2026-08-31T12:00:00Z"},
        ]}})
    )

    headlines = await news.get_headlines(limit=10)

    # bbc + cnn (both hit newsapi.org) + guardian = 3 results, newest first
    assert len(headlines) == 3
    assert headlines[0]["title"] == "Newer"


@respx.mock
async def test_source_error_returns_empty_list_not_exception(news):
    respx.get("https://newsapi.org/v2/top-headlines").mock(return_value=httpx.Response(500))
    respx.get("https://open-platform.theguardian.com/search").mock(return_value=httpx.Response(500))

    headlines = await news.get_headlines(source="bbc")

    assert headlines == []


async def test_source_without_api_key_returns_empty(monkeypatch):
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)
    service = NewsService()

    headlines = await service.get_headlines(source="bbc")

    assert headlines == []


async def test_unknown_source_falls_through_to_all_sources(news):
    """source= is only honored when it's a recognized key; anything else
    is treated the same as no source filter."""
    with respx.mock:
        respx.get("https://newsapi.org/v2/top-headlines").mock(return_value=httpx.Response(200, json={"articles": []}))
        respx.get("https://open-platform.theguardian.com/search").mock(
            return_value=httpx.Response(200, json={"response": {"results": []}})
        )
        headlines = await news.get_headlines(source="reuters")
        assert headlines == []
