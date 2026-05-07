import asyncio
import random
from concurrent.futures import ThreadPoolExecutor

from .config import cfg, logger
from .llm_client import summarize, evaluate_title
from .notify import post_summary
from .scraper import scrape_article, TooManyRequestsError, DomainConnectionError
from .search import fetch_zenn_tag, fetch_from_searxng, fetch_from_index_page
from .storage import ensure_db, get_pending, set_summary, upsert_article
import time
from urllib.parse import urlparse
from collections import deque

# Global state for domain cooldowns
# Format: {"domain": expire_timestamp}
domain_cooldowns = {}


def run_fetch():
    logger.info("[WORKER] Starting run_fetch (Prioritizing Direct Index Pages)")
    total_start = time.time()
    
    # Shuffle target sites to randomize search order
    target_sites = list(cfg.TARGET_SITES)
    random.shuffle(target_sites)

    for site in target_sites:
        name = site["name"]
        domain = site["domain"]
        keywords = site.get("keywords") or [""]
        index_urls = site.get("index_urls") or []
        
        # Check if domain is in cooldown
        if time.time() < domain_cooldowns.get(domain, 0):
            logger.info(f"[WORKER] Skipping {domain} due to active cooldown.")
            continue

        # 1. Try direct index pages if available (HTML scraping)
        if index_urls:
            for idx in index_urls:
                logger.info(f"[WORKER] Scraping index: {name} -> {idx}")
                fetch_from_index_page(idx, domain, limit=5)
                time.sleep(random.uniform(5, 10))

        # 2. Try keywords (SearXNG search)
        for kw in keywords:
            # Skip empty keyword if we already scraped indices to save search load
            if not kw and index_urls:
                continue
            
            logger.info(f"[WORKER] Searching SearXNG: {name} ({domain}) | keyword='{kw}'")
            if domain == "zenn.dev":
                fetch_zenn_tag(kw or "python", limit=3, time_range="month")
            else:
                fetch_from_searxng(domain, kw, limit=3, time_range="month")
            
            sleep_range = cfg.DOMAIN_RATE_LIMIT.get(domain, cfg.DOMAIN_RATE_LIMIT["others"])
            s = random.uniform(*sleep_range)
            time.sleep(s)
            
        logger.info(f"[WORKER] Buffer sleep (10s) between domains for search safety")
        time.sleep(10)
    
    total_duration = time.time() - total_start
    logger.info(f"[WORKER] Finished run_fetch in {total_duration:.2f}s")


def process_article(row, fast_filter=False):
    url, title, site, raw_text = row
    domain = urlparse(url).netloc
    
    # Check cooldown
    if time.time() < domain_cooldowns.get(domain, 0):
        logger.debug(f"[WORKER] Domain {domain} is in cooldown, skipping {url}")
        return False

    logger.info(f"[WORKER] Processing article: {url}")
    proc_start = time.time()
    
    try:
        if not raw_text:
            # If fast filter is enabled, check title before scraping
            if fast_filter:
                logger.info(f"[WORKER] Fast filter enabled. Evaluating title: {title}")
                if not evaluate_title(title):
                    logger.info(f"[WORKER] Fast filter skipped article: {url}")
                    # Mark as processed with a skip meta
                    set_summary(url, "[Skipped by fast filter]", {"is_useful_for_python_student": False, "importance": 1})
                    return True

            # Scrape with safety and 429 detection
            scraped = scrape_article(url)
            text = scraped.get("text", "")
            if not text:
                logger.warning(f"[WORKER] No content extracted for {url}. Marking as processed to avoid infinite loop.")
                # Mark as processed with failure message
                set_summary(url, "[Failed to extract content]", {"is_useful_for_python_student": False, "importance": 0})
                return True # Now returns True to signal it's "done"
            
            new_title = scraped.get("title", title)
            upsert_article(
                url=url, title=new_title, site=site, raw_text=text
            )
        else:
            text = raw_text
        
        # call LLM
        res = summarize(text)
        
        # Determine summary and meta robustly.
        summary = None
        meta = None
        if isinstance(res, dict):
            summary = res.get("summary")
            meta = res
        else:
            # ... (handling raw string fallback)
            raw = str(res or "").strip()
            meta = {"raw": raw, "summary": raw, "is_useful_for_python_student": True}
            summary = raw

        if summary:
            set_summary(url, summary, meta)
            
            is_useful = meta.get("is_useful_for_python_student", False)
            is_ai_news = meta.get("is_ai_news", False)
            importance = meta.get("importance", 0)
            
            # 1. Post to AI News channel if it's significant AI news
            if is_ai_news:
                logger.info(f"[WORKER] Posting significant AI News to Slack for {url}")
                try:
                    display_summary = f"🚀 *AI News Release*\n{summary}\n\n*Importance:* {importance}/5"
                    post_summary(title, url, display_summary, channel_id=cfg.SLACK_NEWS_CHANNEL_ID)
                except Exception as e:
                    logger.error(f"Failed to post AI news for {url}: {e}")

            # 2. Post to Python channel if it's useful (and importance >= 4)
            if is_useful and importance >= 4:
                reason = meta.get("reason_for_usefulness", "")
                logger.info(f"[WORKER] Posting summary to Slack for {url} (Importance: {importance})")

                try:
                    # Append reason to summary for Slack post
                    display_summary = f"{summary}\n\n*重要度:* {importance}/5\n*有用性判定理由 (Python歴3年向け):*\n{reason}"
                    post_summary(title, url, display_summary)
                    logger.info(f"[WORKER] Successfully posted summary for {url}")
                except Exception as e:
                    logger.error(f"Failed to post summary for {url}: {e}")
            
            if not is_ai_news and not (is_useful and importance >= 4):
                logger.info(f"Article skipped (Not useful enough or low importance): {url} (Useful={is_useful}, AI News={is_ai_news}, Importance={importance})")
        else:
            logger.warning(f"No summary generated for {url}")

        proc_duration = time.time() - proc_start
        logger.info(f"[WORKER] Article processing finished in {proc_duration:.2f}s")
        
        # Integrate Crawl-delay with custom rate limits
        sleep_range = cfg.DOMAIN_RATE_LIMIT.get(domain, cfg.DOMAIN_RATE_LIMIT["others"])
        config_delay = random.uniform(*sleep_range)
        
        # Retrieve crawl_delay from cache
        from .scraper import is_allowed_by_robots
        _, robots_delay = is_allowed_by_robots(url)
        
        effective_delay = max(robots_delay, config_delay)
        logger.debug(f"[WORKER] Sleeping for {effective_delay:.2f}s (Max of Robots:{robots_delay}s, Config:{config_delay:.2f}s)")
        time.sleep(effective_delay)
        return True

    except TooManyRequestsError:
        logger.warning(f"[WORKER] 429 Error for {domain}. Setting cooldown for 10 minutes.")
        domain_cooldowns[domain] = time.time() + 600
        return False
    except DomainConnectionError as e:
        logger.warning(f"[WORKER] Domain Connection Error for {domain}. Setting cooldown for 1 hour. Error: {e}")
        domain_cooldowns[domain] = time.time() + 3600
        return False
    except Exception as e:
        logger.exception(f"[WORKER] Unexpected error processing {url}: {e}")
        return True


def main_loop(fast_filter=False):
    logger.info(f"[WORKER] Starting main loop (fast_filter={fast_filter})")
    ensure_db()
    run_fetch()
    
    processed_count = 0
    while True:
        # Batch size 100 to protect memory
        pending = get_pending(limit=100)
        if not pending:
            break
            
        # Group by domain
        domain_queues = {}
        for row in pending:
            url = row[0]
            domain = urlparse(url).netloc
            if domain not in domain_queues:
                domain_queues[domain] = deque()
            domain_queues[domain].append(row)
            
        logger.info(f"[WORKER] Batch of {len(pending)} articles distributed across {len(domain_queues)} domains")
        
        active_domains = list(domain_queues.keys())
        while active_domains:
            for domain in list(active_domains):
                # If domain in cooldown, immediately skip this domain for this entire batch
                if time.time() < domain_cooldowns.get(domain, 0):
                    logger.info(f"[WORKER] Removing domain {domain} from current batch due to active cooldown.")
                    active_domains.remove(domain)
                    continue

                if not domain_queues[domain]:
                    active_domains.remove(domain)
                    continue
                
                row = domain_queues[domain].popleft()
                if process_article(row, fast_filter=fast_filter):
                    processed_count += 1
            
            # Yield to other processes
            time.sleep(0.5)

    logger.info(f"[WORKER] Main loop execution finished. Total processed: {processed_count}")


if __name__ == "__main__":
    main_loop()
