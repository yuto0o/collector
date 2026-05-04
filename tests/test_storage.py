import os

from src import storage


def test_db_create(tmp_path):
    path = tmp_path / "test.db"
    storage.cfg.DB_PATH = str(path)
    storage.ensure_db()
    assert path.exists()
