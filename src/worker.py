import asyncio
import random
from concurrent.futures import ThreadPoolExecutor

from .config import cfg
from .llm_client import summarize
from .notify import post_summary
from .scraper import scrape_zenn
from .search import fetch_zenn_tag
from .storage import ensure_db, get_pending, set_summary, upsert_article


def run_fetch():
    fetch_zenn_tag("python", limit=20)


def process_article(row):
    url, title, site, raw_text = row
    if not raw_text:
        scraped = scrape_zenn(url)
        text = scraped.get("text", "")
        upsert_article(
            url=url, title=scraped.get("title", title), site=site, raw_text=text
        )
    else:
        text = raw_text
    # call LLM
    res = summarize(text)
    # Determine summary and meta robustly. If LLM returns an explanatory "thinking"
    # text (not a JSON summary), treat it as failure and fall back to article snippet.
    summary = None
    meta = None
    if isinstance(res, dict):
        summary = res.get("summary")
        meta = res
    else:
        raw = str(res or "").strip()
        meta = {"raw": raw}
        low = raw.lower()
        # Heuristics to detect chain-of-thought / reasoning dumps
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
            # treat as no summary so fallback will be used
            summary = ""
        else:
            summary = raw
    set_summary(url, summary, meta)
    post_summary(title, url, summary)


def main_loop():
    ensure_db()
    # initial fetch
    run_fetch()
    # process pending
    pending = get_pending(limit=50)
    for row in pending:
        process_article(row)
    # resend any processed articles that were not posted due to earlier failures
    try:
        from .storage import get_unposted_processed

        unposted = get_unposted_processed(limit=100)
        for url, title, summary in unposted:
            try:
                post_summary(title, url, summary)
            except Exception:
                # ignore and continue
                continue
    except Exception:
        pass


if __name__ == "__main__":
    main_loop()
