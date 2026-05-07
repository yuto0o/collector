# Collector

技術記事の自動収集・要約・有用性判定通知システム。

## プロジェクト概要
このプロジェクトは、Python学習歴3年以上の高度な知識を持つ学生をターゲットに、国内外の主要な技術メディア、コミュニティ、ブログから厳選された知見を抽出し、日本語で要約してSlackに通知する自動化システムです。



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
LLAMA_MODEL="qwen3.6"                          # 使用するモデル名

# Slack設定
SLACK_BOT_TOKEN="xoxb-..."                    # Slack Bot Token
SLACK_CHANNEL_ID="C0..."                      # 投稿先のメインチャンネルID
SLACK_NEWS_CHANNEL_ID="C0..."                 # AIニュース（Gemma4リリース等）の通知先チャンネルID

# ボット設定
BOT_EMAIL="your_email@example.com"             # クローラーの身元用連絡先

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

### 4. テストの実行 (Docker)
Docker環境内でテストを実行するには、以下のコマンドを使用します。
```bash
docker compose run --rm -v $(pwd)/tests:/app/tests -e PYTHONPATH=. collector pytest tests
```

---

## 🛠 使い方

### 記事収集の実行（トリガー）
システムはAPIリクエストを受けることで収集を開始します。



####  高速実行（事前絞り込みモード） ★推奨（こっち使ってください！！！）
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

## 主要機能
1.  **インテリジェントな横断検索と直接収集**
    *   **マルチモード収集:** HTMLインデックスページの直接スクレイピング、SearXNGによる横断検索、RSSフィードの3層構造で記事を網羅。
    *   **期間フィルタ:** 検索エンジンにおいて直近1ヶ月（month）以内の記事に限定。
    *   **AIニュース自動検知:** 重要なAIモデルのリリース（例：Gemma 4 MTP対応など）を検知し、専用のSlackチャンネルへ優先通知。
    *   **事前絞り込み (Fast Filter):** 本文取得前にタイトルだけでLLMが一次審査を行い、不要な記事を高速にスキップ。
    *   **ゼロ件対策 (Fallback Expand):** 検索結果が少ない場合、5秒のバッファを挟んでから段階的に検索範囲を広げて再取得。
2.  **究極の生存性・安全性ポリシー（完全体）**
    *   **robots.txtの完全遵守:** スクレイピング前に `robots.txt` を取得・解析。`Disallow` を避けるだけでなく、**`Crawl-delay` も秒単位で遵守**。取得失敗時は安全のため5秒の遅延を強制。
    *   **統合レート制御:** `Crawl-delay` と独自の設定値を比較し、**常に最も安全な（長い）待ち時間を自動採用**。
    *   **ドメイン別クールダウン（動的・高速スキップ）:** 
        *   429 (Too Many Requests) 検知時：該当ドメインを **10分間** 停止。
        *   接続エラー/DNSエラー検知時：該当ドメインを **1時間** 停止。
        *   クールダウン中は処理キューから即座に除外され、無駄なループを発生させません。
    *   **取得失敗記事の自動リトライ (TTL):** 本文取得に失敗した記事は3日間、再アクセスを禁止。3日経過後に自動で再試行リストに追加されます。
    *   **再クロール防止:** 一度正常に判定・通知された記事はDBを削除しない限り二度と取得しません。
    *   **ドメイン分散処理 (Round-Robin):** 同一サイトへの連続アクセスを物理的に排除する並び替えアルゴリズム。
    *   **User-Agentローテーション:** 連絡先付きボット名をランダムに使用。
3.  **LLMによる超厳格な判定**
    *   「基礎・入門・AIトレンド・一般的なニュース」をすべて排除。
    *   「高度な設計・深い最適化・実装詳細」のみを許可（重要度4以上必須）。
    *   ただし、AIニュースとして検知されたものは例外的に通知。
4.  **Slack通知 & 永続化**
    *   有用な記事のみ、判定理由と共にSlack投稿。SQLiteによる完全な重複排除。

## 技術スタック
*   **Search Engine:** SearXNG (Self-hosted)
*   **Scraper:** Scrapling, BeautifulSoup, RobotParser
*   **LLM Integration:** Llama API互換 (gpt-4o互換モード)
*   **Database:** SQLite3
*   **Stability:** Tenacity (Retry), Domain Round-Robin Scheduler, Classified Backoff
