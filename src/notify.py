from slack_sdk import WebClient

from .config import cfg
from . import storage

client = WebClient(token=cfg.SLACK_BOT_TOKEN) if cfg.SLACK_BOT_TOKEN else None


def post_summary(title: str, url: str, summary: str, channel_id: str = None):
    # Deduplicate: avoid posting the same article twice
    try:
        if storage.is_already_posted(url):
            print("Already posted, skipping:", url)
            return
    except Exception:
        # If storage check fails, proceed to avoid data loss
        pass

    target_channel = channel_id or cfg.SLACK_CHANNEL_ID
    if not client:
        print(f"Slack token not configured; would post to {target_channel}:", title, url, summary)
        # Do not mark posted when posting is not attempted
        return

    # If summary empty, try to use article excerpt as fallback
    if not summary:
        try:
            art = storage.get_article(url)
            raw = art.get("raw_text") if art else None
            if raw:
                excerpt = raw.strip()[:300] + ("…" if len(raw.strip()) > 300 else "")
                summary_to_post = excerpt
            else:
                summary_to_post = "要約を生成できませんでした。"
        except Exception:
            summary_to_post = "要約を生成できませんでした。"
    else:
        summary_to_post = summary

    # Japanese formatted message
    text = f"*{title}*\n{url}\n\n*要約*:\n{summary_to_post}"
    try:
        res = client.chat_postMessage(channel=target_channel, text=text)
    except Exception as e:
        # On post failure, do not mark posted so it can be retried later
        print("Slack post failed:", e)
        return

    # mark posted (store timestamp)
    try:
        ts = None
        # Slack WebClient returns a SlackResponse with `.data`; try multiple ways
        try:
            ts = res.get("ts")
        except Exception:
            try:
                ts = getattr(res, "data", {}).get("ts")
            except Exception:
                ts = None
        storage.mark_posted(url, ts, slack_ts=ts)
    except Exception:
        pass
