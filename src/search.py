import time
import requests
import feedparser

from .storage import upsert_article
from .config import cfg, logger


def fetch_zenn_tag(tag: str = "python", limit: int = 20):
    """Fetch article URLs for a given tag.

    If `cfg.SEARXNG_URL` is set, query SearXNG and extract result URLs. Otherwise
    fall back to Zenn's RSS feed.
    """
    logger.info(f"Fetching articles for tag: {tag} (limit: {limit})")
    
    # Try SearXNG if configured
    if cfg.SEARXNG_URL:
        logger.info(f"Trying SearXNG at {cfg.SEARXNG_URL}")
        try:
            params = {"q": f"site:zenn.dev {tag}", "format": "json", "count": limit}
            search_url = cfg.SEARXNG_URL.rstrip("/") + "/search"
            resp = requests.get(search_url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results") or []
            logger.info(f"SearXNG returned {len(results)} results")
            
            count = 0
            for r in results:
                if count >= limit:
                    break
                url = r.get("url")
                title = r.get("title") or r.get("name") or url
                if not url or "zenn.dev" not in url:
                    continue
                try:
                    upsert_article(url=url, title=title, site="zenn", raw_text="")
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to upsert article {url}: {e}")
            
            if count > 0:
                logger.info(f"Successfully fetched {count} articles from SearXNG")
                return
        except Exception as e:
            logger.warning(f"SearXNG failed: {e}. Falling back to RSS.")

    # Zenn provides tag RSS e.g. https://zenn.dev/topics/python/feed
    logger.info("Fetching via Zenn RSS feed")
    feed_url = f"https://zenn.dev/topics/{tag}/feed"
    try:
        d = feedparser.parse(feed_url)
        logger.info(f"RSS feed returned {len(d.entries)} entries")
        for entry in d.entries[:limit]:
            url = entry.link
            title = entry.title
            try:
                # We'll fetch raw text later via scraper
                upsert_article(url=url, title=title, site="zenn", raw_text="")
            except Exception as e:
                logger.error(f"Failed to upsert article from RSS {url}: {e}")
    except Exception as e:
        logger.error(f"RSS feed failed: {e}")
