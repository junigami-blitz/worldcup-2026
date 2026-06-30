# World Cup 2026 サイト — プラン3：ニュース・自動更新・公開 実装プラン

**Goal:** Google News RSS（鍵不要）から日本語ニュースを取得して `data/news.json` を生成しサイトに「ニュース」ページを追加。さらに GitHub Actions（cron × schedule_gate）で「試合時間帯だけ自動更新→ビルド→GitHub Pages デプロイ」を実現する。football-data / YouTube は APIキーが要るため、鍵を環境変数から読み、未設定時は安全にスキップするスキャフォールドに留める。

**Architecture:** Plan1/2 と同じく、純粋関数（RSSパーサー・整形）と薄いI/O層（fetch_news・build）を分離。RSSパースは fixture でTDD。取得失敗時は既存 `data/news.json` を保持。

**Tech Stack:** Python標準ライブラリのみ（`xml.etree.ElementTree`・`email.utils`・`urllib.parse.quote`）、取得は `subprocess+curl`、テストは pytest。CI は GitHub Actions、公開は GitHub Pages。

## Global Constraints
- 日本語・TDD・`git add`明示パス・`html.escape`徹底。
- APIキー（football-data, YouTube）は**絶対コミットしない**。GitHub Secrets 経由・環境変数読み。
- 取得失敗で既存JSONを壊さない（前回値保持）。
- 取得できない項目（ハイライト等）はセクション自動非表示。

---

### Task A: ニュース取得（Google News RSS）
- `wc/news.py`:
  - `parse_news_rss(xml_text, limit=20) -> list[dict]`（純粋）: `[{title, link, source, published(YYYY-MM-DD or 生文字列)}]`。
  - `NEWS_URL(query)`: `https://news.google.com/rss/search?q=...&hl=ja&gl=JP&ceid=JP:ja`（queryはURLエンコード）。
  - `main(out_dir="data", query="ワールドカップ2026", fetcher=fetch_text, now_iso=None) -> int`: 取得→パース→`data/news.json`（`{generated_at, items}`）。失敗時は既存保持で `1`。
- TDD: RSS fixture → title/link/source/published 抽出、pubDate整形、limit、壊れたXMLで空。

### Task B: ニュースページ
- `wc/render.py` に `news_list(items, limit)` 追加（純粋・エスケープ）。
- `wc/build_site.py` に `build_news(news)` 追加、`main` で `data/news.json`（無ければ空）を読み `news.html` 生成。ニュースタブを `_TABS` に追加（トップ/グループ/決勝T/ランキング/ニュース）。アイテム0件ならセクション非表示メッセージ。
- TDD: news_list がタイトル/リンク/出典を含みエスケープされること、build_news/main が news.html を生成すること。

### Task C: YouTubeハイライト（鍵ゲートのスキャフォールド）
- `wc/youtube.py`:
  - `pick_highlight(items, allow_channels) -> dict|None`（純粋）: 検索結果から許可チャンネル優先で1件選ぶ。
  - `main(... api_key=env)`: 鍵が無ければ即 `print("SKIP: YOUTUBE_API_KEY未設定")` で `0`（パイプライン継続）。鍵があれば終了済み試合のうち未解決分だけ検索（クォータ節約）。
- TDD: pick_highlight の許可リスト優先・該当なし時 None のみ（ネットワークなし）。実検索は鍵が無いためスキップ設計。

### Task D: GitHub Actions × Pages
- `.github/workflows/update.yml`:
  - cron（広め）+ 手動 `workflow_dispatch`。
  - steps: checkout → setup-python → `python -m wc.schedule_gate`（exit0=RUN）→ RUN時のみ `update_data`・`news.main`・(`youtube.main`鍵あれば)・`build_site` → 変更を `data/`・`site/` にコミット&push → Pages アーティファクトを `actions/upload-pages-artifact`(site/) → `actions/deploy-pages`。
  - 窓外は早期終了（gateがexit1なら後続スキップ）。
  - Secrets: `FOOTBALL_DATA_API_KEY`・`YOUTUBE_API_KEY`（任意）。
- `.github/workflows/structure-daily.yml`: 1日1回 `update_data`+`news`+`build_site`（試合の有無に関わらず骨格/ニュース更新）。
- Pages 権限: `permissions: contents: write, pages: write, id-token: write`。
- README に「GitHubリポ作成→Secrets登録→Pages有効化」の手順を追記。

---

## Self-Review（spec照合）
- ニュース（Google News RSS 日本語）: Task A/B ✅
- 自動更新（cron×ゲート）・Pages公開: Task D ✅
- YouTubeハイライト（公式優先→フォールバック）: Task C で許可リストロジック＋鍵ゲート（実検索は鍵登録後）⏳
- football-data 鮮度補完: 鍵登録後の拡張として update_data に統合予定（本プランではスキャフォールド方針のみ明記）⏳
- 取得失敗時の前回値保持・無データ非表示: 各 main / render で踏襲 ✅
