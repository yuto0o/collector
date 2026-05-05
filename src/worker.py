import asyncio
import random
from concurrent.futures import ThreadPoolExecutor

from .config import cfg, logger
from .llm_client import summarize, evaluate_title
from .notify import post_summary
from .scraper import scrape_article
from .search import fetch_zenn_tag, fetch_from_searxng
from .storage import ensure_db, get_pending, set_summary, upsert_article
import time


def run_fetch():
    logger.info("[WORKER] Starting run_fetch for all target sites with keywords")
    total_start = time.time()
    for site in cfg.TARGET_SITES:
        name = site["name"]
        domain = site["domain"]
        keywords = site.get("keywords") or [""]
        
        for kw in keywords:
            logger.info(f"[WORKER] Fetching: {name} ({domain}) | keyword='{kw}'")
            if domain == "zenn.dev":
                fetch_zenn_tag(kw or "python", limit=20)
            else:
                fetch_from_searxng(domain, kw, limit=10)
            
            time.sleep(random.uniform(1, 2))
    
    total_duration = time.time() - total_start
    logger.info(f"[WORKER] Finished run_fetch in {total_duration:.2f}s")


def process_article(row, fast_filter=False):
    url, title, site, raw_text = row
    logger.info(f"[WORKER] Processing article: {url}")
    proc_start = time.time()
    
    if not raw_text:
        # If fast filter is enabled, check title before scraping
        if fast_filter:
            logger.info(f"[WORKER] Fast filter enabled. Evaluating title: {title}")
            if not evaluate_title(title):
                logger.info(f"[WORKER] Fast filter skipped article: {url} (Title: {title})")
                # Mark as processed with a skip meta
                set_summary(url, "[Skipped by fast filter]", {"is_useful_for_python_student": False, "importance": 1})
                return

        scraped = scrape_article(url)
        text = scraped.get("text", "")
        if not text:
            logger.warning(f"Failed to scrape text for {url}")
            return
        
        new_title = scraped.get("title", title)
        upsert_article(
            url=url, title=new_title, site=site, raw_text=text
        )
    else:
        logger.info(f"Article text already exists for {url}")
        text = raw_text
    
    # call LLM
    logger.info(f"Calling LLM for summarization: {url}")
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
        logger.info(f"Setting summary for {url}")
        set_summary(url, summary, meta)
        
        # Check usefulness
        is_useful = meta.get("is_useful_for_python_student")
        importance = meta.get("importance", 0)
        
        if is_useful is None:
            is_useful = True
        
        # Double strict check: must be useful AND importance >= 4
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
        else:
            logger.info(f"Article skipped (Not useful enough or low importance): {url} (Useful={is_useful}, Importance={importance})")
    else:
        logger.warning(f"No summary generated for {url}")

    proc_duration = time.time() - proc_start
    logger.info(f"[WORKER] Article processing finished in {proc_duration:.2f}s")


def main_loop(fast_filter=False):
    logger.info(f"[WORKER] Starting main loop (fast_filter={fast_filter})")
    ensure_db()
    
    # initial fetch
    run_fetch()
    
    # process pending until none left
    processed_count = 0
    while True:
        pending = get_pending(limit=50)
        if not pending:
            break
            
        logger.info(f"[WORKER] Found {len(pending)} pending articles to process (Total processed so far: {processed_count})")
        for row in pending:
            try:
                process_article(row, fast_filter=fast_filter)
                processed_count += 1
            except Exception as e:
                logger.exception(f"[WORKER] Error processing article {row[0]}: {e}")
            
    # resend any processed articles that were not posted due to earlier failures
    try:
        from .storage import get_unposted_processed

        unposted = get_unposted_processed(limit=100)
        if unposted:
            logger.info(f"[WORKER] Found {len(unposted)} unposted processed articles")
            for url, title, summary in unposted:
                try:
                    logger.info(f"[WORKER] Retrying Slack post for {url}")
                    post_summary(title, url, summary)
                    logger.info(f"[WORKER] Successfully posted summary for {url} on retry")
                except Exception as e:
                    logger.error(f"[WORKER] Failed retry post for {url}: {e}")
                    continue
    except Exception as e:
        logger.error(f"[WORKER] Error in unposted processing: {e}")
    
    logger.info(f"[WORKER] Main loop execution finished. Total processed: {processed_count}")


if __name__ == "__main__":
    main_loop()
