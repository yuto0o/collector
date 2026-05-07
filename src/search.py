import time
import random
from datetime import datetime, timedelta, timezone
import requests
import feedparser
from urllib.parse import urlparse, urljoin

from .storage import upsert_article
from .config import cfg, logger


def fetch_from_index_page(index_url: str, domain: str, limit: int = 5):
    """Scrape an index page (e.g. blog home) for article links.
    Uses Scrapling first to handle dynamic content/anti-bot.
    """
    from .scraper import is_allowed_by_robots
    allowed, delay = is_allowed_by_robots(index_url)
    if not allowed:
        logger.warning(f"[INDEX] Scraping index DISALLOWED by robots.txt for {index_url}")
        return 0
    
    if delay > 0:
        time.sleep(delay)

    logger.info(f"[INDEX] Fetching index page: {index_url}")
    start_time = time.time()
    
    try:
        # Try Scrapling first (more robust)
        from .scraper import HAS_SCRAPLING_LIB
        text = ""
        html = ""
        soup = None
        
        if HAS_SCRAPLING_LIB:
            from scrapling import Fetcher
            fetcher = Fetcher()
            page = fetcher.get(index_url)
            # Check 403/429
            status = getattr(page, "status", 200)
            if status == 200:
                from bs4 import BeautifulSoup
                # Scrapling page object usually has a .body attribute for raw HTML
                html_content = getattr(page, "body", "") or getattr(page, "text", "")
                if html_content:
                    soup = BeautifulSoup(html_content, "lxml")
            else:
                logger.warning(f"[INDEX] Scrapling returned status {status} for {index_url}")

        # Fallback to requests if Scrapling failed
        if soup is None:
            ua = random.choice(cfg.USER_AGENTS)
            resp = requests.get(index_url, timeout=cfg.GLOBAL_TIMEOUT, headers={"User-Agent": ua})
            resp.raise_for_status()
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.content, "lxml")
        
        # Find all <a> tags
        links = soup.find_all("a", href=True)
        discovered = []
        for l in links:
            href = l["href"]
            if href.startswith("/"):
                href = urljoin(index_url, href)
            
            if domain not in href or href == index_url:
                continue

            # Heuristics for "article-like" URLs
            path = urlparse(href).path
            is_article = any(y in path for y in ["/2024/", "/2025/", "/2026/", "/articles/", "/blog/", "/posts/"])
            
            if not is_article:
                if len(path.strip("/").split("/")) >= 2:
                    is_article = True

            noise = ["/tags/", "/category/", "/author/", "/search", "/login", "/signup", "/archive", "?", "#"]
            if any(n in href for n in noise):
                is_article = False
                
            if is_article:
                discovered.append((href, l.get_text(strip=True) or href))
        
        unique_links = []
        seen = set()
        for h, t in discovered:
            if h not in seen:
                unique_links.append((h, t))
                seen.add(h)
        
        count = 0
        for url, title in unique_links[:limit]:
            try:
                upsert_article(url=url, title=title, site=domain, raw_text="")
                count += 1
            except Exception as e:
                logger.debug(f"[INDEX] Failed to upsert {url}: {e}")
                
        duration = time.time() - start_time
        logger.info(f"[INDEX] Discovered {count} articles from {index_url} in {duration:.2f}s")
        return count
    except Exception as e:
        logger.warning(f"[INDEX] Failed to scrape index {index_url}: {e}")
        return 0


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
        # Use GLOBAL_TIMEOUT but ensure it's at least 15s for SearXNG consistency
        timeout = max(cfg.GLOBAL_TIMEOUT, 15)
        resp = requests.get(search_url, params=params, timeout=timeout)
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


def fetch_zenn_tag(tag: str = "python", limit: int = 3, time_range: str = ""):
    """Fetch article URLs for a given tag.

    Try SearXNG first, then fall back to Zenn's RSS feed.
    """
    logger.info(f"[SEARCH] Fetching Zenn articles for tag: {tag}")
    
    count = fetch_from_searxng("zenn.dev", tag, limit, time_range=time_range)
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
