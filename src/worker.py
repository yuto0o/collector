import asyncio
import random
from concurrent.futures import ThreadPoolExecutor

from .config import cfg, logger
from .llm_client import summarize
from .notify import post_summary
from .scraper import scrape_zenn
from .search import fetch_zenn_tag
from .storage import ensure_db, get_pending, set_summary, upsert_article


def run_fetch():
    logger.info("Starting run_fetch")
    fetch_zenn_tag("python", limit=20)
    logger.info("Finished run_fetch")


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
        raw = str(res or "").strip()
        meta = {"raw": raw}
        low = raw.lower()
        reasoning_indicators = [
            "thinking process",
            "analyze user input",
            "here's a thinking",
            "here's a thinking process",
            "draft summary",
            "identify key information",
            "analysis",
            "reasoning",
        ]
        long_explanatory = raw.count("\n") > 5 or len(raw) > 400
        if any(ind in low for ind in reasoning_indicators) or long_explanatory:
            logger.info("LLM returned reasoning/long explanatory text instead of a concise summary.")
            summary = ""
        else:
            summary = raw

    if summary:
        logger.info(f"Setting summary for {url}")
        set_summary(url, summary, meta)
        logger.info(f"Posting summary to Slack for {url}")
        try:
            post_summary(title, url, summary)
            logger.info(f"Successfully posted summary for {url}")
        except Exception as e:
            logger.error(f"Failed to post summary for {url}: {e}")
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
