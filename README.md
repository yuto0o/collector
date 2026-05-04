# Collector (Zenn PoC)

PoC collector that fetches article URLs, scrapes content, sends to llama.cpp server for summarization, stores results in SQLite, and posts to Slack.

Run locally with Docker Compose:

```bash
# cd collector
docker compose build
docker compose up -d
docker compose logs -f collector
```

Processing flow (簡潔):

- フェッチ: `src.search.fetch_zenn_tag` が記事URLを収集して `articles` テーブルに `processed=0` で保存します。
- スクレイプ: `src.scraper.scrape_zenn` が各 URL をスクレイプして `raw_text` を保存します。
- 要約: `src.worker` が未処理の記事を取り出し、`src.llm_client.summarize` を呼び出して要約を取得します。要約が空の場合は記事本文の先頭を代替要約として使います。
- 永続化: 要約とメタ情報を `src.storage.set_summary` で保存し、`processed=1` にします。
- 通知: `src.notify.post_summary` が Slack に日本語で投稿します。投稿成功時に `posted_at` と `slack_ts` を `articles` に保存し、二重投稿を防ぎます。投稿失敗時は DB を保留のままとして後で再試行できます。

必須（事前確認）:
- `.env` に `SLACK_BOT_TOKEN`（Bot OAuth token）と `SLACK_CHANNEL_ID` が設定されていること。
- Bot に `chat:write` 権限があり、投稿先チャンネルに招待されていること。


test
```bash
docker run --rm -v "$PWD":/usr/src/app -w /usr/src/app -e PYTHONPATH=/usr/src/app python:3.11-slim bash -lc "apt-get update && apt-get install -y gcc libxml2-dev libxslt1-dev build-essential && pip install -r requirements.txt && PYTHONPATH=/usr/src/app pytest -q"
```
