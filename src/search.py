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


def fetch_from_searxng(domain: str, query: str = "", limit: int = 3, time_range: str = ""):
    """Generic function to fetch articles from a specific domain using SearXNG."""
    if not cfg.SEARXNG_URL:
        logger.warning("SearXNG URL not configured, skipping search.")
        return 0

    full_query = f"site:{domain} {query}".strip()
    logger.info(f"[SEARCH] Starting SearXNG: query='{full_query}', domain={domain} (limit={limit})")
    start_time = time.time()
    try:
        params = {
            "q": full_query,
            "format": "json",
            "count": limit,
        }
        if time_range:
            params["time_range"] = time_range
            
        search_url = cfg.SEARXNG_URL.rstrip("/") + "/search"
        # Use GLOBAL_TIMEOUT
        resp = requests.get(search_url, params=params, timeout=cfg.GLOBAL_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results") or []
        duration = time.time() - start_time
        logger.info(f"[SEARCH] SearXNG finished in {duration:.2f}s. Found {len(results)} raw results for {domain}")
        
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
                logger.error(f"[SEARCH] Failed to upsert article {url}: {e}")
        
        # Zero Result Fallback: if no valid articles stored, try once more with higher limit
        if count == 0 and limit < 10:
            logger.info(f"[SEARCH] 0 articles stored for {domain}. Triggering fallback expansion (limit=10) after 5s buffer.")
            time.sleep(5)
            return fetch_from_searxng(domain, query, limit=10, time_range=time_range)

        logger.info(f"[SEARCH] Successfully stored {count} articles for {domain}")
        return count
    except Exception as e:
        duration = time.time() - start_time
        logger.warning(f"[SEARCH] SearXNG failed for {domain} after {duration:.2f}s: {e}")
        return 0


def fetch_zenn_tag(tag: str = "python", limit: int = 3):
    """Fetch article URLs for a given tag.

    Try SearXNG first, then fall back to Zenn's RSS feed.
    """
    logger.info(f"[SEARCH] Fetching Zenn articles for tag: {tag}")
    
    count = fetch_from_searxng("zenn.dev", tag, limit)
    if count > 0:
        return

    # Zenn provides tag RSS e.g. https://zenn.dev/topics/python/feed
    logger.info("[SEARCH] Falling back to Zenn RSS feed")
    start_time = time.time()
    feed_url = f"https://zenn.dev/topics/{tag}/feed"
    try:
        # Note: feedparser doesn't use standard timeout easily, but it's usually fast
        d = feedparser.parse(feed_url)
        duration = time.time() - start_time
        logger.info(f"[SEARCH] RSS feed fetched in {duration:.2f}s. Entries: {len(d.entries)}")
        added_count = 0
        for entry in d.entries:
            if added_count >= limit:
                break
            
            if not is_recent(entry.get("published_parsed")):
                continue

            url = entry.link
            title = entry.title
            try:
                upsert_article(url=url, title=title, site="zenn.dev", raw_text="")
                added_count += 1
            except Exception as e:
                logger.error(f"[SEARCH] Failed to upsert RSS article {url}: {e}")
        
        # Zenn RSS Fallback Expand
        if added_count == 0 and limit < 10:
            logger.info("[SEARCH] 0 articles from Zenn RSS. Retrying RSS with limit=10")
            # Recurse with higher limit
            return fetch_zenn_tag(tag, limit=10)

        logger.info(f"[SEARCH] Added {added_count} recent articles from RSS")
    except Exception as e:
        logger.error(f"[SEARCH] RSS feed failed: {e}")
