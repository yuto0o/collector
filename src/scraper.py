import requests
from bs4 import BeautifulSoup
try:
    from scrapling import Fetcher
    HAS_SCRAPLING_LIB = True
except ImportError:
    HAS_SCRAPLING_LIB = False

from .config import cfg, logger


def scrape_zenn(url: str) -> dict:
    """Scrape article text and title for a given URL.

    We try:
    1. Scrapling library (direct)
    2. Local requests + BeautifulSoup (fallback)
    """
    logger.info(f"Scraping URL: {url}")
    
    # 1. Try Scrapling library directly
    if HAS_SCRAPLING_LIB:
        logger.info(f"Using Scrapling library (Fetcher) for {url}")
        try:
            fetcher = Fetcher()
            page = fetcher.get(url)
            title = getattr(page, "title", "")
            text = getattr(page, "text", "")
            if title or text:
                logger.info(f"Scrapling library successful for {url}")
                return {"title": title, "text": text}
        except Exception as e:
            logger.warning(f"Scrapling library failed for {url}: {e}")

    # Local scraping fallback
    logger.info(f"Falling back to local scraping for {url}")
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "lxml")
        # Zenn article main content
        main = soup.find("main") or soup
        # Remove scripts and nav
        for tag in main.find_all(["script", "style", "nav", "aside"]):
            tag.decompose()
        paragraphs = [
            p.get_text(strip=True) for p in main.find_all(["p", "h1", "h2", "h3", "li"])
        ]
        text = "\n\n".join([p for p in paragraphs if p])
        title_tag = soup.find("meta", attrs={"property": "og:title"})
        title = (
            title_tag["content"] if title_tag else soup.title.string if soup.title else ""
        )
        logger.info(f"Local scraping successful for {url}")
        return {"title": title, "text": text}
    except Exception as e:
        logger.error(f"Local scraping failed for {url}: {e}")
        return {"title": "", "text": ""}
