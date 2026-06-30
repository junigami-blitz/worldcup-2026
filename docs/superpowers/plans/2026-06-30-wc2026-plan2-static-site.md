# World Cup 2026 サイト — プラン2：静的サイト生成 実装プラン

**Goal:** プラン1が生成する `data/structure.json`・`data/rankings.json` を読み込み、日テレ風v2デザイン（白基調・ロイヤルブルー・控えめ赤・Oswald等幅数字・ヘアライン）の静的HTMLサイトを `site/` に生成する。`python -m wc.build_site` で `site/index.html`・`site/groups.html`・`site/knockout.html`・`site/rankings.html` ＋ `site/assets/style.css` が生成される。

**Architecture:** 純粋なHTMLレンダリング関数（入力=dict、出力=HTML文字列）と、ファイル読み書きの薄いI/O層（build_site）を分離。レンダリング関数はTDD。CSSは `templates/style.css` に置き build時に `site/assets/` へコピー。外部依存なし（Python標準ライブラリのみ）。

**Tech Stack:** Python 3.11+（標準ライブラリのみ、`html.escape` でエスケープ）、テストは pytest。

## Global Constraints
- 言語/コメントは日本語。TDD必須（先に失敗テスト）。
- `git add -A` 禁止、明示パスで add。
- 動的テキスト（チーム名・選手名）は必ず `html.escape` でエスケープ。
- 取得できない項目（ハイライト・ニュース等）はセクションごと自動非表示（壊さない）。
- 全パスはリポジトリルート `/Users/member1/agents/WorldCupWebsite` 基準。

## データ前提（プラン1の出力）
- `structure.json`: `{name, generated_at, groups:[{name,teams}], teams:[{name,fifa_code,flag_icon,group,confed,continent}], matches:[...]}`
- `rankings.json`: `{generated_at, standings:{ "Group A":[行...] }, scorers:[{name,team,goals,penalties}]}`
- 試合dict: `{round,stage("group"|"knockout"),group,date,time_local,kickoff_utc,team1,team2,played,score:{ft,ht},goals1,goals2,ground}`

## ファイル構成
| ファイル | 責務 |
|---|---|
| `wc/i18n.py` | チーム名 英→日 / ラウンド名 英→日 / 不明時フォールバック |
| `wc/render.py` | 純粋レンダリング関数（フラグメント＋ページシェル） |
| `wc/build_site.py` | data/*.json読込→4ページ生成→assetsコピー |
| `templates/style.css` | v2デザインCSS（静的） |
| `site/` | 生成物（index/groups/knockout/rankings.html + assets/style.css） |
| `tests/test_i18n.py` / `tests/test_render.py` / `tests/test_build_site.py` | テスト |

---

### Task 1: 国際化（チーム名・ラウンド名の日本語化）
- `jp_team(name)`: 既知48チームは日本語、未知は入力英語をそのまま返す。
- `jp_round(round_name)`: "Round of 32"→"ベスト32", "Round of 16"→"ベスト16", "Quarter-final"→"準々決勝", "Semi-final"→"準決勝", "Match for third place"→"3位決定戦", "Final"→"決勝", "Matchday N"→"第N節"。未知はそのまま。
- TDD: 既知/未知/Matchday数字抽出をテスト。

### Task 2: レンダリング関数（純粋）
- `_flag(team_obj)`: 絵文字を `<span class="flag">` で包む（無ければ空）。
- `_esc(s)`: `html.escape`。
- `goal_line(goals1, team1, goals2, team2)`: "9' 久保 ・ 67' 三笘" 形式（得点者がいなければ空文字）。
- `match_card(match, teams_by_name)`: スコア（未消化は "vs"）・チーム名(日)・国旗・得点者行を含むカードHTML。
- `standings_table(group_name_jp, rows, teams_by_name)`: 順位表。上位2行に突破ライン左罫（`is-advance`クラス）、3位はプレーオフ枠候補として中間色。
- `scorers_table(scorers, top_n)`: 得点王テーブル（得点降順、PK内訳）。
- `page_shell(title, active_tab, body_html, generated_at)`: 共通シェル（ヘッダ・テキストタブ＋下線・フッタ・CSSリンク）。`active_tab` で現在タブに赤下線。
- TDD: 各関数が想定の主要部分文字列・クラスを含むこと、エスケープされること、未消化試合が "vs" になること。

### Task 3: ページ組み立てとビルド
- `build_index(structure, rankings)`: 直近開催日の結果カード群＋大会サマリー（参加48・進行状況）。
- `build_groups(structure, rankings)`: 12グループ各ブロック（順位表＋そのグループの試合カード）。
- `build_knockout(structure)`: ラウンド順（R32→R16→QF→SF→3位→決勝）にカラム表示。
- `build_rankings(rankings)`: 得点王テーブル。
- `main(data_dir="data", out_dir="site", templates_dir="templates")`: 各JSON読込→4ページ書き出し→`style.css`を`site/assets/`へコピー。`structure.json`が無ければ `1` を返す。
- TDD: `main` が4つのHTML＋assetsを生成し主要内容を含むこと（tmp_path＋サンプルJSON）。実データでのスモークビルドも実施。

---

## Self-Review（spec照合）
- 非SPA・静的HTML生成: build_site ✅
- v2デザイン（白/青/控えめ赤/Oswald/ヘアライン/突破ライン左罫）: style.css + render ✅
- グループ順位表・日程結果 / 決勝T / 得点王: Task3 ✅
- ハイライト・ニュース・アシスト等: 現データに無いため**セクション自動非表示**（spec準拠、Plan3で追加）。
- 国旗: 絵文字チップで全48対応（spec「CSS chip」からの現実的逸脱を明記）。
- 完全ブラケット線画: Plan3のポリッシュ（Plan2はラウンド別カラム）。
