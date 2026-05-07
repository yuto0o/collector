import pytest
import time
from src import notify, search, scraper, llm_client, worker


@pytest.fixture(autouse=True)
def disable_network(monkeypatch):
    """Prevent external network calls during tests."""
    monkeypatch.setattr(notify, "post_summary", lambda *a, **k: None)
    monkeypatch.setattr(search, "fetch_zenn_tag", lambda *a, **k: None)
    monkeypatch.setattr(search, "fetch_from_searxng", lambda *a, **k: None)
    monkeypatch.setattr(search, "fetch_from_index_page", lambda *a, **k: None)
    monkeypatch.setattr(scraper, "scrape_article", lambda url: {"text": "", "title": ""})
    monkeypatch.setattr(llm_client._default, "summarize", lambda text: {"summary": "dummy", "highlights": []})
    monkeypatch.setattr(worker, "run_fetch", lambda: None)
    monkeypatch.setattr(time, "sleep", lambda s: None)
    yield
