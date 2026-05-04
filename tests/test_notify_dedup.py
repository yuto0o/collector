from src import storage
import importlib
from src import notify as notify_module


def test_notify_dedup(tmp_path, monkeypatch):
    # reload inside the test to undo autouse monkeypatch in conftest
    notify = importlib.reload(notify_module)
    db = tmp_path / "test.db"
    storage.cfg.DB_PATH = str(db)
    storage.ensure_db()

    url = "https://example.com/fake"
    title = "Fake"
    summary = "要約"
    # insert article row
    storage.upsert_article(url=url, title=title, site="zenn", raw_text="text")

    calls = []

    class DummyClient:
        def chat_postMessage(self, channel=None, text=None):
            calls.append((channel, text))
            return {"ts": "123"}

    monkeypatch.setattr(notify, "client", DummyClient())

    # First call should post
    notify.post_summary(title, url, summary)
    assert len(calls) == 1

    # Second call should be skipped due to dedup
    notify.post_summary(title, url, summary)
    assert len(calls) == 1
