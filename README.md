# Collector: プロフェッショナル仕様・技術記事収集システム

## 📝 プロジェクト概要
このプロジェクトは、Python学習歴3年以上の高度な知識を持つエンジニアや学生をターゲットにした、自動記事収集・要約・通知システムです。国内外の28以上の主要技術メディアから、真に価値のある高度な知見（設計パターン、最適化、実装詳細など）を抽出し、日本語で要約してSlackへ通知します。

---

## 🚀 クイックスタート（起動方法）

### 1. 事前準備
- **Docker & Docker Compose** がインストールされていること。
- **ローカルLLMサーバー**（Llama API / OpenAI API互換）が動作していること。
- **Slack Bot** のトークンと投稿先チャンネルIDが用意されていること。

### 2. 環境設定 (`.env`)
プロジェクトのルートディレクトリに `.env` ファイルを作成（env.exampleをコピー）し、以下の内容を設定してください。
```env
# LLM設定 (Llama API互換サーバー)
LLAMA_ENDPOINT=""  # LLMのURL
LLAMA_API_KEY="your_api_key"                  # APIキー（あれば）

# Slack設定
SLACK_BOT_TOKEN="xoxb-..."                    # Slack Bot Token
SLACK_CHANNEL_ID="C0..."                      # 投稿先のチャンネルID

# システム設定
DB_PATH=./data/collector.db                   # SQLiteデータベースの保存先
```

### 3. サービスの起動
以下のコマンドで、検索エンジン（SearXNG）とメインアプリケーション（Collector）を同時に起動します。
```bash
docker compose up -d --build
```
- **SearXNG**: `http://localhost:8888` で動作（内部通信用）
- **Collector API**: `http://localhost:8080` で動作

---

## 🛠 使い方

### 記事収集の実行（トリガー）
システムはAPIリクエストを受けることで収集を開始します。

#### A. 通常実行（全件精査モード）
すべての検索結果に対して本文スクレイピングとフル要約を試みます。
```bash
curl -X POST http://localhost:8080/trigger/fetch
```

#### B. 高速実行（事前絞り込みモード） ★推奨（こっち使ってください！！！）
本文を取りに行く前に、タイトルだけでLLMが一次審査を行います。入門記事などを瞬時にスキップできるため、非常に高速です。（LLMが強いならね）
```bash
curl -X POST "http://localhost:8080/trigger/fetch?fast_filter=true"
```

### 監視と確認
処理はバックグラウンドで続行されます。進捗は以下のコマンドでリアルタイムに確認できます。
```bash
docker logs collector -f
```
- `[SEARCH]`: 検索状況
- `[ROBOTS]`: 規約（robots.txt）の確認状況
- `[SCRAPE]`: 本文抽出状況
- `[LLM]`: 有用性判定と要約の推論状況
- `[WORKER]`: Slack投稿やクールダウンの制御状況

---

## 🛡 生存性・安全性ポリシー（プロ仕様のこだわり）
当システムは、対象サイトに負荷をかけず、BAN（アクセス禁止）されないことを最優先に設計されています。

- **robots.txtの完全遵守**: `Disallow` パスを避け、`Crawl-delay` 指示に従って秒単位で待機します。
- **ドメイン別レート制限 & 分散処理**: 同一サイトへの連続アクセスを物理的に排除するラウンドロビン方式を採用。
- **動的クールダウン**: 429エラーなら10分、接続エラーなら1時間、そのドメインを自動的に避けます。
- **User-Agentローテーション**: 連絡先入りの公式ボット名を複数使い分け、透明性を確保。
- **超厳格なフィルタリング**: 3年以上の経験者が唸る記事以外は、一切Slackを鳴らしません。

---

## 🔧 メンテナンス

### データの保存先
収集した記事や処理状況は `data/collector.db` (SQLite) に保存されます。

### 既知のURLを忘れる（再取得したい場合）
一度処理したURLは3日間再取得しません。テスト等で再度取得したい場合は、DBをクリアしてください。
```bash
sqlite3 data/collector.db "DELETE FROM articles"
```

---

## 🏗 技術スタック
- **Search Engine**: SearXNG (Self-hosted)
- **Scraper**: Scrapling (Playwright/Fetcher), BeautifulSoup, RobotParser
- **LLM**: OpenAI API 互換クライアント (httpx)
- **Database**: SQLite3
- **Stability**: Tenacity (Retry), Domain-level Scheduler
