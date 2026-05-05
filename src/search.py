import time
from datetime import datetime, timedelta, timezone
import requests
import feedparser

from .storage import upsert_article
from .config import cfg, logger


def is_recent(published_struct, days=14):
    """Check if the given time structure is within the last 'days'."""
    if not published_struct:
        return True  # Assume recent if no date is found
    dt = datetime(*published_struct[:6], tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    return now - dt < timedelta(days=days)


def fetch_from_searxng(domain: str, query: str = "", limit: int = 10, time_range: str = "month"):
    """Generic function to fetch articles from a specific domain using SearXNG."""
    if not cfg.SEARXNG_URL:
        return 0

    full_query = f"site:{domain} {query}".strip()
    logger.info(f"Trying SearXNG for {domain} with query '{query}'")
    try:
        params = {
            "q": full_query,
            "format": "json",
            "count": limit,
            "time_range": time_range
        }
        search_url = cfg.SEARXNG_URL.rstrip("/") + "/search"
        resp = requests.get(search_url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results") or []
        logger.info(f"SearXNG returned {len(results)} results for {domain}")
        
        count = 0
        for r in results:
            if count >= limit:
                break
            url = r.get("url")
            title = r.get("title") or r.get("name") or url
            if not url or domain not in url:
                continue
            try:
                upsert_article(url=url, title=title, site=domain, raw_text="")
                count += 1
            except Exception as e:
                logger.error(f"Failed to upsert article {url}: {e}")
        return count
    except Exception as e:
        logger.warning(f"SearXNG failed for {domain}: {e}")
        return 0


def fetch_zenn_tag(tag: str = "python", limit: int = 20):
    """Fetch article URLs for a given tag.

    Try SearXNG first, then fall back to Zenn's RSS feed.
    """
    logger.info(f"Fetching Zenn articles for tag: {tag}")
    
    count = fetch_from_searxng("zenn.dev", tag, limit)
    if count > 0:
        logger.info(f"Successfully fetched {count} articles from SearXNG for Zenn")
        return

    # Zenn provides tag RSS e.g. https://zenn.dev/topics/python/feed
    logger.info("Falling back to Zenn RSS feed")
    feed_url = f"https://zenn.dev/topics/{tag}/feed"
    try:
        d = feedparser.parse(feed_url)
        logger.info(f"RSS feed returned {len(d.entries)} entries")
        added_count = 0
        for entry in d.entries:
            if added_count >= limit:
                break
            
            # Date filtering: 14 days
            if not is_recent(entry.get("published_parsed")):
                continue

            url = entry.link
            title = entry.title
            try:
                upsert_article(url=url, title=title, site="zenn", raw_text="")
                added_count += 1
            except Exception as e:
                logger.error(f"Failed to upsert article from RSS {url}: {e}")
        logger.info(f"Added {added_count} recent articles from RSS")
    except Exception as e:
        logger.error(f"RSS feed failed: {e}")
