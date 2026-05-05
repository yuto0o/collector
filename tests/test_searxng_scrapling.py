import types

import pytest

import importlib
from src import search as _search_module, scraper as _scraper_module
from src import config

# When conftest autouse fixtures mock module functions, reload modules locally
def reload_search():
    importlib.reload(_search_module)
    return _search_module

def reload_scraper():
    importlib.reload(_scraper_module)
    return _scraper_module


class DummyResp:
    def __init__(self, status=200, json_data=None, text="", content=b"", headers=None):
        self.status_code = status
        self._json = json_data or {}
        self.text = text
        self.content = content or text.encode("utf-8")
        self.headers = headers or {"Content-Type": "application/json"}

    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            raise Exception(f"status {self.status_code}")

    def json(self):
        return self._json


def test_fetch_zenn_tag_uses_searxng(monkeypatch):
    called = {}

    def fake_get(url, params=None, timeout=None):
        called['url'] = url
        assert url.endswith('/search')
        return DummyResp(json_data={"results": [{"url": "https://zenn.dev/foo", "title": "T"}]})

    search = reload_search()
    monkeypatch.setattr(config.cfg, 'SEARXNG_URL', 'http://fake:8888')
    monkeypatch.setattr('requests.get', fake_get)

    # avoid DB writes by replacing upsert_article on reloaded module
    items = []

    def fake_upsert_article(url, title, site, raw_text):
        items.append((url, title, site, raw_text))

    monkeypatch.setattr(search, 'upsert_article', fake_upsert_article)

    search.fetch_zenn_tag(tag='python', limit=5)
    assert items and items[0][0] == 'https://zenn.dev/foo'


def test_scrape_zenn_uses_scrapling(monkeypatch):
    # Return JSON response from Scrapling
    def fake_post(endpoint, json=None, timeout=None):
        assert 'extract' in endpoint or endpoint.endswith('/extract') or endpoint.endswith('8000')
        return DummyResp(json_data={"title": "Sample", "text": "Hello world"})

    scraper = reload_scraper()
    monkeypatch.setattr(config.cfg, 'SCRAPLING_URL', 'http://fake-scrap:8000')
    monkeypatch.setattr('requests.post', fake_post)

    res = scraper.scrape_zenn('https://example.com/article')
    assert res['title'] == 'Sample'
    assert 'Hello world' in res['text']
