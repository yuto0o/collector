import pytest
from src import notify, search, scraper, llm_client


@pytest.fixture(autouse=True)
def disable_network(monkeypatch):
    """Prevent external network calls during tests."""
    monkeypatch.setattr(notify, "post_summary", lambda *a, **k: None)
    monkeypatch.setattr(search, "fetch_zenn_tag", lambda *a, **k: None)
    monkeypatch.setattr(scraper, "scrape_zenn", lambda url: {"text": "", "title": ""})
    monkeypatch.setattr(llm_client._default, "summarize", lambda text: {"summary": "dummy", "highlights": []})
    yield
