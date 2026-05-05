import asyncio
import random
from concurrent.futures import ThreadPoolExecutor

from .config import cfg, logger
from .llm_client import summarize
from .notify import post_summary
from .scraper import scrape_zenn
from .search import fetch_zenn_tag, fetch_from_searxng
from .storage import ensure_db, get_pending, set_summary, upsert_article
import time


def run_fetch():
    logger.info("Starting run_fetch for all target sites")
    for site in cfg.TARGET_SITES:
        name = site["name"]
        domain = site["domain"]
        query = site["query"]
        
        logger.info(f"Fetching articles from {name} ({domain})")
        if domain == "zenn.dev":
            fetch_zenn_tag(query or "python", limit=20)
        else:
            fetch_from_searxng(domain, query, limit=10)
        
        # Add a small random sleep between sites to be polite
        time.sleep(random.uniform(1, 3))
    
    logger.info("Finished run_fetch for all target sites")


def process_article(row):
    url, title, site, raw_text = row
    logger.info(f"Processing article: {url} (title: {title})")
    
    if not raw_text:
        logger.info(f"Article text is empty, scraping {url}")
        scraped = scrape_zenn(url)
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

    logger.info(f"LLM Result meta for {url}: is_useful={meta.get('is_useful_for_python_student')}, reason_len={len(meta.get('reason_for_usefulness', ''))}")

    if summary:
        logger.info(f"Setting summary for {url}")
        set_summary(url, summary, meta)
        
        # Check usefulness
        is_useful = meta.get("is_useful_for_python_student")
        if is_useful is None:
            is_useful = True
        reason = meta.get("reason_for_usefulness", "")
        
        if is_useful:
            logger.info(f"Posting summary to Slack for {url} (Reason: {reason})")
            try:
                # Append reason to summary for Slack post
                display_summary = f"{summary}\n\n*有用性判定理由 (Python歴3年向け):*\n{reason}"
                post_summary(title, url, display_summary)
                logger.info(f"Successfully posted summary for {url}")
            except Exception as e:
                logger.error(f"Failed to post summary for {url}: {e}")
        else:
            logger.info(f"Article deemed not useful for Python student: {url}")
    else:
        logger.warning(f"No summary generated for {url}")


def main_loop():
    logger.info("Starting main loop")
    ensure_db()
    
    # initial fetch
    run_fetch()
    
    # process pending
    pending = get_pending(limit=50)
    logger.info(f"Found {len(pending)} pending articles to process")
    
    for row in pending:
        try:
            process_article(row)
        except Exception as e:
            logger.exception(f"Error processing article {row[0]}: {e}")
            
    # resend any processed articles that were not posted due to earlier failures
    try:
        from .storage import get_unposted_processed

        unposted = get_unposted_processed(limit=100)
        if unposted:
            logger.info(f"Found {len(unposted)} unposted processed articles")
            for url, title, summary in unposted:
                try:
                    logger.info(f"Retrying Slack post for {url}")
                    post_summary(title, url, summary)
                    logger.info(f"Successfully posted summary for {url} on retry")
                except Exception as e:
                    logger.error(f"Failed retry post for {url}: {e}")
                    continue
    except Exception as e:
        logger.error(f"Error in unposted processing: {e}")
    
    logger.info("Main loop execution finished")


if __name__ == "__main__":
    main_loop()
