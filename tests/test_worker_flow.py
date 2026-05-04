import os
import tempfile

from src import scraper, search, storage


def test_full_flow_monkeypatch(monkeypatch, tmp_path):
    dbpath = tmp_path / "collector.db"
    # Point config DB
    storage.cfg.DB_PATH = str(dbpath)
    storage.ensure_db()

    # Insert a fake article
    url = "https://example.com/fake"
    title = "Fake Article"
    site = "zenn"
    raw_text = "This is a test article about Python and LLMs."
    storage.upsert_article(url, title, site, raw_text)

    # Monkeypatch summarize to avoid calling external LLM
    from src.llm_client import _default

    def fake_summarize(text):
        return {"summary": "テスト要約: 短く。", "highlights": ["点1", "点2"]}

    monkeypatch.setattr(_default, "summarize", lambda text: fake_summarize(text))
    # Ensure no actual Slack/network calls during test
    from src import notify

    monkeypatch.setattr(notify, "post_summary", lambda *a, **k: None)

    # Run worker main loop
    from src.worker import main_loop

    main_loop()

    # Check DB updated
    rows = storage.get_pending(limit=10)
    assert len(rows) == 0
