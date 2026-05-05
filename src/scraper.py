import requests
import time
from bs4 import BeautifulSoup
try:
    from scrapling import Fetcher
    HAS_SCRAPLING_LIB = True
except ImportError:
    HAS_SCRAPLING_LIB = False

from .config import cfg, logger


def scrape_article(url: str) -> dict:
    """Scrape article text and title for any URL.

    We try:
    1. Scrapling library (direct)
    2. Local requests + BeautifulSoup (fallback)
    """
    logger.info(f"[SCRAPE] Starting: {url}")
    start_time = time.time()
    
    # 1. Try Scrapling library directly
    if HAS_SCRAPLING_LIB:
        logger.info(f"[SCRAPE] Using Scrapling library for {url}")
        try:
            fetcher = Fetcher()
            page = fetcher.get(url)
            title = getattr(page, "title", "")
            text = getattr(page, "text", "")
            if title or text:
                duration = time.time() - start_time
                logger.info(f"[SCRAPE] Scrapling successful in {duration:.2f}s. Title: '{title[:30]}...', Text length: {len(text)}")
                return {"title": title, "text": text}
        except Exception as e:
            logger.warning(f"[SCRAPE] Scrapling library failed for {url}: {e}")

    # Local scraping fallback
    logger.info(f"[SCRAPE] Falling back to generic BeautifulSoup for {url}")
    try:
        resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "lxml")
        
        # Generic content extraction
        # Try common article containers
        main_content = soup.find(["article", "main", "div[role='main']"]) or soup.body or soup
        
        # Remove scripts, nav, style, etc.
        for tag in main_content.find_all(["script", "style", "nav", "aside", "header", "footer", "form"]):
            tag.decompose()
            
        paragraphs = [
            p.get_text(strip=True) for p in main_content.find_all(["p", "h1", "h2", "h3", "li"])
        ]
        text = "\n\n".join([p for p in paragraphs if p])
        
        title_tag = soup.find("meta", attrs={"property": "og:title"}) or soup.find("title")
        title = ""
        if title_tag:
            title = title_tag.get("content") if title_tag.name == "meta" else title_tag.get_text()
        
        duration = time.time() - start_time
        if text:
            logger.info(f"[SCRAPE] Generic successful in {duration:.2f}s. Title: '{title[:30]}...', Text length: {len(text)}")
        else:
            logger.warning(f"[SCRAPE] Generic failed (no text) in {duration:.2f}s for {url}")
            
        return {"title": title, "text": text}
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"[SCRAPE] Generic failed after {duration:.2f}s for {url}: {e}")
        return {"title": "", "text": ""}
