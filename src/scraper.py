import requests
import time
import random
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse

try:
    from scrapling import Fetcher
    HAS_SCRAPLING_LIB = True
except ImportError:
    HAS_SCRAPLING_LIB = False

from .config import cfg, logger

# Cache for robots.txt parsers to avoid re-fetching
# Format: {"domain": (RobotFileParser, expire_timestamp)}
_robots_cache = {}


class TooManyRequestsError(Exception):
    """Raised when 429 status code is encountered."""
    pass


class DomainConnectionError(Exception):
    """Raised when DNS or Connection errors occur (Server likely down)."""
    pass


def is_allowed_by_robots(url: str) -> tuple[bool, float]:
    """Check robots.txt for the given URL. Returns (is_allowed, crawl_delay)."""
    parsed = urlparse(url)
    domain = f"{parsed.scheme}://{parsed.netloc}"
    robots_url = f"{domain}/robots.txt"
    
    now = time.time()
    if domain in _robots_cache:
        rp, expire = _robots_cache[domain]
        if now < expire:
            # Respect crawl delay if specified
            delay = rp.crawl_delay("*") or 0.0
            return rp.can_fetch("*", url), float(delay)
            
    logger.info(f"[ROBOTS] Fetching robots.txt for {domain}")
    try:
        rp = RobotFileParser()
        rp.set_url(robots_url)
        # Use a short timeout for robots.txt
        ua = cfg.USER_AGENTS[0]
        resp = requests.get(robots_url, timeout=5, headers={"User-Agent": ua})
        if resp.status_code == 404:
            rp.allow_all = True
        else:
            rp.parse(resp.text.splitlines())
        
        # Cache for 1 day (86400s)
        _robots_cache[domain] = (rp, now + 86400)
        delay = rp.crawl_delay("*") or 0.0
        return rp.can_fetch("*", url), float(delay)
    except Exception as e:
        logger.warning(f"[ROBOTS] Failed to fetch robots.txt for {domain}: {e}. Assuming allowed with safety delay (5s).")
        # Cache failure briefly to avoid hammering robots.txt
        _robots_cache[domain] = (None, now + 600)
        return True, 5.0


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((requests.exceptions.RequestException, TooManyRequestsError)),
    reraise=True
)
def _do_scrape(url: str, headers: dict) -> dict:
    """Internal function with retry logic."""
    try:
        # 1. Try Scrapling library directly
        if HAS_SCRAPLING_LIB:
            try:
                fetcher = Fetcher()
                page = fetcher.get(url)
                status = getattr(page, "status", 200)
                if status == 429:
                    raise TooManyRequestsError("429 Too Many Requests via Scrapling")
                
                title = getattr(page, "title", "")
                text = getattr(page, "text", "")
                if title or text:
                    return {"title": title, "text": text}
            except TooManyRequestsError:
                raise
            except Exception as e:
                logger.debug(f"[SCRAPE] Scrapling attempt failed: {e}")

        # 2. Local fallback
        resp = requests.get(url, timeout=cfg.GLOBAL_TIMEOUT, headers=headers)
        if resp.status_code == 429:
            raise TooManyRequestsError("429 Too Many Requests")
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.content, "lxml")
        main_content = soup.find(["article", "main", "div[role='main']"]) or soup.body or soup
        if not main_content:
            return {"title": "", "text": ""}

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
            
        return {"title": title, "text": text}
    except requests.exceptions.ConnectionError as e:
        # Classify as DomainConnectionError for specialized cooldown
        raise DomainConnectionError(f"Connection failed: {e}")
    except TooManyRequestsError:
        raise
    except Exception as e:
        # Other RequestExceptions will be retried by tenacity
        raise


def scrape_article(url: str) -> dict:
    """Scrape article text and title with robots.txt check, crawl-delay, and 429 detection."""
    # 0. Robots.txt check
    allowed, delay = is_allowed_by_robots(url)
    if not allowed:
        logger.warning(f"[ROBOTS] Scraping DISALLOWED by robots.txt for {url}")
        return {"title": "[Blocked by robots.txt]", "text": ""}
    
    if delay > 0:
        logger.info(f"[ROBOTS] Respecting Crawl-delay: {delay}s for {url}")
        time.sleep(delay)

    logger.info(f"[SCRAPE] Starting: {url}")
    start_time = time.time()
    
    ua = random.choice(cfg.USER_AGENTS)
    headers = {"User-Agent": ua}
    logger.debug(f"[SCRAPE] Using UA: {ua}")

    try:
        result = _do_scrape(url, headers)
        duration = time.time() - start_time
        if result.get("text"):
            logger.info(f"[SCRAPE] Successful in {duration:.2f}s. Text length: {len(result['text'])}")
        else:
            logger.warning(f"[SCRAPE] Finished with no text extracted for {url}")
        return result
    except TooManyRequestsError:
        logger.warning(f"[SCRAPE] 429 Persistent Error for {url}")
        raise
    except DomainConnectionError as e:
        logger.warning(f"[SCRAPE] Connection error for {url}: {e}")
        raise
    except Exception as e:
        logger.error(f"[SCRAPE] All retry attempts failed for {url}: {e}")
        return {"title": "", "text": ""}
