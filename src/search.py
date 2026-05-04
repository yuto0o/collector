import time

import feedparser

from .storage import upsert_article


def fetch_zenn_tag(tag: str = "python", limit: int = 20):
    # Zenn provides tag RSS e.g. https://zenn.dev/topics/python/feed
    feed_url = f"https://zenn.dev/topics/{tag}/feed"
    d = feedparser.parse(feed_url)
    for entry in d.entries[:limit]:
        url = entry.link
        title = entry.title
        try:
            # We'll fetch raw text later via scraper
            upsert_article(url=url, title=title, site="zenn", raw_text="")
        except Exception:
            pass
