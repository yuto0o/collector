# Collector

技術記事の自動収集・要約・有用性判定通知システム。

## プロジェクト概要
このプロジェクトは、Python学習歴3年程度の学生をターゲットに、国内外の主要な技術メディア、コミュニティ、ブログから「本当に有用な情報」だけを抽出し、日本語で要約してSlackに通知する自動化システムです。

## 主要機能
1.  **マルチサイト横断検索・収集**
    *   SearXNGを活用し、28の主要技術サイトを横断的に検索。
    *   ZennについてはRSSフィードによる補完的な収集も実施。
    *   **期間フィルタリング:** 公開から14日（2週間）以内の新しい記事のみを対象。
2.  **インテリジェントな本文抽出**
    *   Scraplingライブラリ（Playwright/Fetcher）を使用し、動的なコンテンツを含む記事からも本文を正確に抽出。
3.  **LLMによる有用性判定と要約**
    *   ローカルLLM（Llama API互換）を使用。
    *   **判定基準:** 「Python歴3年の学生」にとって、基礎を超えた実用的な知見、技術的深み、あるいは興味深いトレンドが含まれているか。
    *   **出力:** 要約（日本語）、ハイライト、重要度（1-5）、有用性フラグ、判定理由。
4.  **Slack通知**
    *   LLMが「有用（True）」と判定した記事のみ、要約と「なぜ有用か」の理由を添えて通知。
5.  **データ永続化**
    *   SQLite（`data/collector.db`）に収集・処理済みの全データを保存し、重複投稿を防止。

## 対象サイト一覧（計28サイト）
*   **国内:** Zenn, Qiita, DevelopersIO, note, Hatena Developer Blog, Speaker Deck, Connpass
*   **コミュニティ:** Reddit (r/LocalLLaMA, r/MachineLearning, r/Python), Hacker News, Stack Overflow Blog
*   **技術ブログ/論文:** Hugging Face (Blog, Papers), arXiv (cs.AI), OpenAI Blog, Anthropic News, Google Research, Meta AI, Microsoft Research
*   **メディア/プラットフォーム:** Towards Data Science, Medium, Substack, GitHub Trending, Papers with Code, Kaggle, Dev.to, LlamaIndex Blog

## セットアップ

### Docker環境（推奨）
1.  `.env` ファイルに以下を設定：
    *   `LLAMA_ENDPOINT`: LLMサーバーURL
    *   `LLAMA_API_KEY`: APIキー
    *   `SLACK_BOT_TOKEN`: Slackトークン
    *   `SLACK_CHANNEL_ID`: 送信先ID
2.  `docker compose up -d --build` で起動。
3.  SearXNG（ポート8888）とCollector（ポート8080）が立ち上がります。

### 実行
*   `curl -X POST http://localhost:8080/trigger/fetch` を叩くことで、全サイトの巡回と処理が開始されます。

## 技術スタック
*   **Language:** Python 3.11
*   **Search Engine:** SearXNG (Self-hosted)
*   **Scraper:** Scrapling (Playwright, curl-cffi)
*   **LLM Integration:** OpenAI API compatible client (httpx)
*   **Database:** SQLite3
*   **Notification:** Slack SDK
