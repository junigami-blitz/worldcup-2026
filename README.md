# World Cup 2026 解説サイト

2026 FIFAワールドカップ（カナダ・メキシコ・USA共催）の試合結果・順位・ランキング・ニュース・ハイライトを無料データソースから自動更新する静的サイト。

## 構成
- データ取得・集計: `wc/`（Python標準ライブラリ + curl）
- 生成データ: `data/*.json`
- 仕様: `docs/superpowers/specs/2026-06-30-worldcup-2026-site-design.md`

## データ更新

    python -m wc.update_data

## ニュース取得（Google News RSS・鍵不要）

    python -m wc.news

## サイト生成

    python -m wc.build_site
    # site/ に index/groups/knockout/rankings/news.html + assets/style.css を生成

## ローカルプレビュー

    cd site && python -m http.server 8765
    # http://localhost:8765/ を開く

## テスト

    pytest

## 自動更新と公開（GitHub Actions + Pages）

`.github/workflows/update.yml` が2時間おき（＋手動実行）に
データ取得→ニュース→サイト生成→GitHub Pages デプロイを行う。

### セットアップ手順
1. GitHub に**公開リポジトリ**を作成し push する（Pages/Actions が無料になる条件）。
2. リポジトリの **Settings → Pages → Build and deployment → Source** を「GitHub Actions」にする。
3. （任意）**Settings → Secrets and variables → Actions** に以下を登録すると拡張機能が有効化される:
   - `YOUTUBE_API_KEY` … 試合ハイライト動画（YouTube Data API v3 無料枠）
   - `FOOTBALL_DATA_API_KEY` … 結果の鮮度補完（football-data.org 無料枠）
4. Actions タブから `データ更新とPagesデプロイ` を手動実行して初回デプロイ。

鍵未設定でも openfootball（鍵不要）＋ニュースだけで完全に動作する。
ハイライト/football-data は鍵が無ければ自動でスキップされる。

### 試合ハイライト（YouTube）について
`YOUTUBE_API_KEY` を登録すると、終了済み試合ごとにハイライト動画を検索し
（クォータ節約のため未取得分のみ）、各試合カードに「▷ ハイライト」リンクを表示する。
取得結果は `data/highlights.json` にキャッシュされ、ワークフローが書き戻して永続化する。
許可チャンネルを厳密化したい場合は `wc/youtube.py` の `DEFAULT_ALLOW_CHANNELS` に
FIFA公式・放送局公式のチャンネルIDを設定する（未設定時は検索最上位を採用）。

### スタメン・スタッツ（API-Football）について
`API_FOOTBALL_KEY` を登録すると、各試合の**スタメン（フォーメーション＋先発XI＋控え）**、
**選手スタッツ**（出場時間・評価・得点・シュート・パス）、**チームスタッツ**（支配率・
シュート等）を取得し、試合詳細ページに表示する。

- 取得元: API-Football（api-sports.io）v3。無料プラン **100リクエスト/日**。
- 登録: https://www.api-sports.io/ または https://dashboard.api-football.com/ で無料登録 →
  APIキー取得 → GitHub Secret `API_FOOTBALL_KEY` に登録。
- 仕組み: ワークフローが `fixtures?league=1&season=2026` で試合IDを紐づけ、終了済み未取得の
  試合だけ `fixtures/lineups`・`fixtures/players`・`fixtures/statistics` を取得して
  `data/lineups.json` にキャッシュ（1回最大12試合でクォータ保護）。
- 鍵が無ければスキップし、各国の登録メンバー（スカッド）を表示する。

### 結果の鮮度補完（football-data.org）について
`FOOTBALL_DATA_API_KEY` を登録すると、openfootball がまだ反映していない試合に
football-data の確定スコアを上書きして鮮度を上げる（得点者は無料枠に無いため
openfootball が後追いで補完）。チーム名の表記差は `wc/footballdata.py` の
`FD_TEAM_ALIASES` で吸収。一致しない試合は上書きせず安全に openfootball を維持する。
