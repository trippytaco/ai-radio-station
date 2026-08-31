"""/news/headlines endpoint routing."""
import radio_api


class StubNewsService:
    def __init__(self, headlines=None, raises=False):
        self._headlines = headlines or []
        self._raises = raises

    async def get_headlines(self, source, limit):
        if self._raises:
            raise RuntimeError("boom")
        return self._headlines


def test_news_headlines_not_configured(client, monkeypatch):
    monkeypatch.setattr(radio_api, "news_service", None)
    resp = client.get("/news/headlines")
    assert resp.status_code == 500


def test_news_headlines_success(client, monkeypatch):
    monkeypatch.setattr(radio_api, "news_service", StubNewsService(headlines=[{"title": "Big story"}]))
    resp = client.get("/news/headlines")
    assert resp.status_code == 200
    assert resp.json()["headlines"][0]["title"] == "Big story"


def test_news_headlines_upstream_error(client, monkeypatch):
    monkeypatch.setattr(radio_api, "news_service", StubNewsService(raises=True))
    resp = client.get("/news/headlines")
    assert resp.status_code == 500
    assert "News error" in resp.json()["detail"]
