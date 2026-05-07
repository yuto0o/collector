import json
import os
import sqlite3
from datetime import datetime

from .config import cfg


def ensure_db():
    os.makedirs(os.path.dirname(cfg.DB_PATH), exist_ok=True)
    conn = sqlite3.connect(cfg.DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            title TEXT,
            site TEXT,
            fetched_at TEXT,
            raw_text TEXT,
            summary TEXT,
            summary_meta TEXT,
            processed INTEGER DEFAULT 0,
            try_count INTEGER DEFAULT 0
        )
        """
    )
    conn.commit()
    # Ensure posted_at column exists for duplicate-post prevention
    try:
        cur.execute("PRAGMA table_info(articles)")
        cols = [r[1] for r in cur.fetchall()]
        if "posted_at" not in cols:
            cur.execute("ALTER TABLE articles ADD COLUMN posted_at TEXT")
        if "slack_ts" not in cols:
            cur.execute("ALTER TABLE articles ADD COLUMN slack_ts TEXT")
            conn.commit()
    except Exception:
        # Non-fatal: ignore if ALTER fails
        pass
    conn.close()


def upsert_article(url: str, title: str, site: str, raw_text: str):
    conn = sqlite3.connect(cfg.DB_PATH)
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute(
        """
        INSERT INTO articles(url, title, site, fetched_at, raw_text, processed, try_count)
        VALUES (?, ?, ?, ?, ?, 0, 0)
        ON CONFLICT(url) DO UPDATE SET title=excluded.title, raw_text=excluded.raw_text, fetched_at=excluded.fetched_at
        """,
        (url, title, site, now, raw_text),
    )
    conn.commit()
    conn.close()


def set_summary(url: str, summary: str, summary_meta: dict):
    conn = sqlite3.connect(cfg.DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "UPDATE articles SET summary=?, summary_meta=?, processed=1 WHERE url=?",
        (summary, json.dumps(summary_meta), url),
    )
    conn.commit()
    conn.close()


def is_already_posted(url: str) -> bool:
    conn = sqlite3.connect(cfg.DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("SELECT posted_at FROM articles WHERE url=?", (url,))
        row = cur.fetchone()
        return bool(row and row[0])
    finally:
        conn.close()


def mark_posted(url: str, ts: str = None, slack_ts: str = None):
    conn = sqlite3.connect(cfg.DB_PATH)
    cur = conn.cursor()
    now = ts or datetime.utcnow().isoformat()
    if slack_ts is not None:
        cur.execute("UPDATE articles SET posted_at=?, slack_ts=? WHERE url=?", (now, slack_ts, url))
    else:
        cur.execute("UPDATE articles SET posted_at=? WHERE url=?", (now, url))
    conn.commit()
    conn.close()


def mark_failed_try(url: str):
    conn = sqlite3.connect(cfg.DB_PATH)
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute(
        "UPDATE articles SET try_count = try_count + 1, fetched_at = ? WHERE url = ?",
        (now, url),
    )
    conn.commit()
    conn.close()


def get_pending(limit: int = 50):
    conn = sqlite3.connect(cfg.DB_PATH)
    cur = conn.cursor()
    # Logic: 
    # 1. processed = 0
    # 2. AND (try_count = 0 OR fetched_at is older than RECRAWL_TTL)
    # Using julianday for date arithmetic in SQLite
    cur.execute(
        """
        SELECT url, title, site, raw_text FROM articles 
        WHERE processed=0 
          AND (try_count = 0 OR (julianday('now') - julianday(fetched_at)) * 86400 > ?)
        LIMIT ?
        """,
        (cfg.RECRAWL_TTL, limit),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_article(url: str):
    conn = sqlite3.connect(cfg.DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id, url, title, site, fetched_at, raw_text, summary, summary_meta, posted_at, slack_ts FROM articles WHERE url=?",
            (url,),
        )
        row = cur.fetchone()
        if not row:
            return None
        keys = [
            "id",
            "url",
            "title",
            "site",
            "fetched_at",
            "raw_text",
            "summary",
            "summary_meta",
            "posted_at",
            "slack_ts",
        ]
        result = dict(zip(keys, row))
        try:
            if result.get("summary_meta"):
                result["summary_meta"] = json.loads(result["summary_meta"])
        except Exception:
            pass
        return result
    finally:
        conn.close()


def is_recently_accessed(url: str, ttl: int = None) -> bool:
    """Check if the URL was fetched within the last 'ttl' seconds."""
    if ttl is None:
        ttl = cfg.RECRAWL_TTL
    conn = sqlite3.connect(cfg.DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT fetched_at FROM articles WHERE url = ?", (url,)
        )
        row = cur.fetchone()
        if not row:
            return False

        try:
            fetched_at_str = row[0]
            if not fetched_at_str:
                return False

            from dateutil.parser import parse as parse_date
            fetched_at = parse_date(fetched_at_str)

            if fetched_at.tzinfo is None:
                from datetime import timezone
                fetched_at = fetched_at.replace(tzinfo=timezone.utc)

            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            return (now - fetched_at).total_seconds() < ttl
        except Exception as e:
            return False
    finally:
        conn.close()


def get_unposted_processed(limit: int = 100):

    """Return list of (url, title, summary) for articles that are processed but not posted."""
    conn = sqlite3.connect(cfg.DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT url, title, summary FROM articles WHERE processed=1 AND (posted_at IS NULL OR posted_at='') LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall()
        return rows
    finally:
        conn.close()
