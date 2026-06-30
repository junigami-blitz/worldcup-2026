# World Cup 2026 サイト — プラン1：データパイプライン基盤 実装プラン

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** openfootball の World Cup 2026 データを取得し、サイトが消費する `data/structure.json`（日程・スコア・得点者・グループ・チーム）と `data/rankings.json`（順位表・得点王）を生成し、試合時間帯だけ処理を走らせるスケジュールゲートを備えた、単体で動くデータパイプラインを作る。

**Architecture:** Pythonの純粋関数（パーサー・集計）と、curlによる取得・アトミックなファイル書き込みの薄いI/O層を分離する。ネットワークI/OとファイルI/Oをパーサーから切り離し、パーサーはfixture文字列でTDDする。最終的に `python -m wc.update_data` で `data/*.json` が生成される。

**Tech Stack:** Python 3.11+（標準ライブラリのみ）、取得は `subprocess + curl`（プロジェクト方針：macOSのSSL証明書エラー回避）、テストは pytest。

## Global Constraints

- 言語/コメントは日本語（CLAUDE.md）。
- TDD必須：実装前に失敗するテストを書く（CLAUDE.md）。
- `git add -A` / `git add .` / `git add --all` 禁止。必ず明示パスで `git add`（git-operations.md、PreToolUseフックで物理ブロック）。
- 新規リポジトリの初回コミットは `safe-init-commit` スキルを必ず使用（git-operations.md）。
- ネット取得は `urllib`/`requests` ではなく `subprocess + curl` を使う（web-scraping.md）。
- 取得失敗時に既存の正常JSONを壊さない（取得失敗→ファイルに触れず終了）。
- 全ファイルパスはリポジトリルート `/Users/member1/agents/WorldCupWebsite` 基準。
- Python 3.11+ 前提（`datetime.fromisoformat`・`timezone` を使用）。

## データソース実構造（確認済み・2026-06-30時点）

`https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/` 配下：

- `worldcup.json`: `{"name", "matches":[{round,date,time,team1,team2,score:{ft:[a,b],ht:[a,b]},goals1:[{name,minute,penalty?,owngoal?}],goals2:[...],group,ground}]}`
  - `score` キーは未消化試合では欠落しうる（→未消化と判定）。
  - `round` は グループ戦が `"Matchday 1"`〜`"Matchday 18"`、ノックアウトが `"Round of 32"` / `"Round of 16"` / `"Quarter-final"` / `"Semi-final"` / `"Match for third place"` / `"Final"`。
  - `time` は `"13:00 UTC-6"` 形式（時刻＋UTCオフセット）。
- `worldcup.groups.json`: `{"groups":[{"name":"Group A","teams":["Mexico",...]}]}`
- `worldcup.teams.json`: `[{"name","name_normalised?","continent","flag_icon","fifa_code","group":"A","confed"}]`

## ファイル構成

| ファイル | 責務 |
|---|---|
| `wc/__init__.py` | パッケージ宣言（空） |
| `wc/atomic_io.py` | `write_json_atomic(path, obj)` / `read_json_or_none(path)`。一時ファイル→`os.replace`でアトミック差し替え |
| `wc/fetch.py` | `fetch_text(url)`：curlサブプロセスで本文取得。失敗時 `FetchError` |
| `wc/kickoff.py` | `parse_kickoff_utc(date_str, time_str)`：`"2026-06-11"`+`"13:00 UTC-6"`→ UTC aware datetime |
| `wc/openfootball.py` | 純粋パーサー：`parse_groups` / `parse_teams` / `parse_matches` / `build_structure` |
| `wc/standings.py` | `compute_standings(matches)`：グループ別順位表 |
| `wc/scorers.py` | `compute_scorers(matches)`：得点王ランキング |
| `wc/schedule_gate.py` | `is_in_match_window(matches, now_utc)` ＋ CLI `main()` |
| `wc/update_data.py` | オーケストレータ。取得→構造化→集計→`data/*.json`書き込み |
| `tests/...` | 各モジュールのテスト |
| `data/` | 生成物（`.gitignore`しない＝サイトが参照。ただし衛生上 `data/*.tmp` は無視） |

---

### Task 1: プロジェクト雛形と初回コミット

**Files:**
- Create: `wc/__init__.py`
- Create: `requirements.txt`
- Create: `pytest.ini`
- Create: `.gitignore`
- Create: `README.md`
- Create: `tests/__init__.py`

**Interfaces:**
- Consumes: なし
- Produces: `wc` パッケージ（以降のモジュール置き場）、pytest実行環境

- [ ] **Step 1: ディレクトリとファイルを作成**

`wc/__init__.py`（空ファイル）、`tests/__init__.py`（空ファイル）を作成。

`requirements.txt`:
```
pytest>=8.0
```

`pytest.ini`:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
```

`.gitignore`:
```gitignore
# Python
__pycache__/
*.pyc
.pytest_cache/
.venv/
venv/

# OS
.DS_Store

# ビジュアルcompanion作業ファイル
.superpowers/

# シークレット（絶対にコミットしない）
.env
.env.*
*.key
*.pem
credentials*.json
service-account*.json

# データの一時ファイル（生成途中）
data/*.tmp
```

`README.md`:
```markdown
# World Cup 2026 解説サイト

2026 FIFAワールドカップ（カナダ・メキシコ・USA共催）の試合結果・順位・ランキング・ニュース・ハイライトを無料データソースから自動更新する静的サイト。

## 構成
- データ取得・集計: `wc/`（Python標準ライブラリ + curl）
- 生成データ: `data/*.json`
- 仕様: `docs/superpowers/specs/2026-06-30-worldcup-2026-site-design.md`

## データ更新
```
python -m wc.update_data
```

## テスト
```
pytest
```
```

- [ ] **Step 2: pytestが起動することを確認**

Run: `cd /Users/member1/agents/WorldCupWebsite && python -m pytest -q`
Expected: `no tests ran`（テスト未作成のため。エラーなく起動すればOK）

- [ ] **Step 3: 初回コミット（safe-init-commit スキルを使用）**

`WorldCupWebsite` を独立gitリポジトリとして初期化する。**`Skill` ツールで `safe-init-commit` を起動**し、その強制ワークフロー（.gitignore確認→`git add -A --dry-run`で追加予定確認→機密検出→明示パスでadd→secret scan→commit）に従う。`docs/` 配下の spec/plan も対象に含める。

Expected: `.env`・`credentials*`等が含まれないことを確認した上で初回コミット完了。

---

### Task 2: アトミックなJSON入出力ユーティリティ

**Files:**
- Create: `wc/atomic_io.py`
- Test: `tests/test_atomic_io.py`

**Interfaces:**
- Produces:
  - `write_json_atomic(path: str | Path, obj) -> None`：`path + ".tmp"` に書いてから `os.replace` で差し替え（同一ディレクトリ前提でアトミック）。親ディレクトリは自動作成。
  - `read_json_or_none(path: str | Path) -> object | None`：存在＆正常JSONなら読み込み、無ければ `None`。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_atomic_io.py`:
```python
import json
from pathlib import Path

from wc.atomic_io import write_json_atomic, read_json_or_none


def test_write_then_read_roundtrip(tmp_path):
    p = tmp_path / "out" / "data.json"
    write_json_atomic(p, {"a": 1, "ja": "日本"})
    assert read_json_or_none(p) == {"a": 1, "ja": "日本"}


def test_read_missing_returns_none(tmp_path):
    assert read_json_or_none(tmp_path / "nope.json") is None


def test_read_corrupt_returns_none(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{ this is not json", encoding="utf-8")
    assert read_json_or_none(p) is None


def test_no_tmp_file_left_behind(tmp_path):
    p = tmp_path / "data.json"
    write_json_atomic(p, {"x": 1})
    assert not (tmp_path / "data.json.tmp").exists()
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python -m pytest tests/test_atomic_io.py -q`
Expected: FAIL（`ModuleNotFoundError: No module named 'wc.atomic_io'`）

- [ ] **Step 3: 最小実装**

`wc/atomic_io.py`:
```python
"""JSONのアトミック書き込みと安全な読み込み。"""
import json
import os
from pathlib import Path


def write_json_atomic(path, obj) -> None:
    """一時ファイルに書いてから os.replace で差し替える。

    途中でクラッシュしても元ファイルが壊れない。親ディレクトリは自動作成。
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)  # 同一ディレクトリ内のアトミックなrename


def read_json_or_none(path):
    """存在し正常なJSONなら読み込む。無い/壊れている場合は None。"""
    path = Path(path)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
```

- [ ] **Step 4: テストが通ることを確認**

Run: `python -m pytest tests/test_atomic_io.py -q`
Expected: PASS（4 passed）

- [ ] **Step 5: コミット**

```bash
git add wc/atomic_io.py tests/test_atomic_io.py
git commit -m "feat: アトミックなJSON入出力ユーティリティを追加"
```

---

### Task 3: キックオフ時刻のUTC変換

**Files:**
- Create: `wc/kickoff.py`
- Test: `tests/test_kickoff.py`

**Interfaces:**
- Produces:
  - `parse_kickoff_utc(date_str: str, time_str: str) -> datetime | None`
    - `date_str="2026-06-11"`, `time_str="13:00 UTC-6"` → `datetime(2026,6,11,19,0,tzinfo=timezone.utc)`
    - 解析不能（空・想定外フォーマット）なら `None`。

UTC-6 は「UTCより6時間遅い」ため `UTC = ローカル時刻 - オフセット(-6) = ローカル + 6h`。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_kickoff.py`:
```python
from datetime import datetime, timezone

from wc.kickoff import parse_kickoff_utc


def test_utc_minus_6():
    assert parse_kickoff_utc("2026-06-11", "13:00 UTC-6") == datetime(
        2026, 6, 11, 19, 0, tzinfo=timezone.utc
    )


def test_utc_minus_4():
    assert parse_kickoff_utc("2026-06-18", "12:00 UTC-4") == datetime(
        2026, 6, 18, 16, 0, tzinfo=timezone.utc
    )


def test_rollover_past_midnight():
    # 20:00 UTC-6 -> 02:00 翌日 UTC
    assert parse_kickoff_utc("2026-06-11", "20:00 UTC-6") == datetime(
        2026, 6, 12, 2, 0, tzinfo=timezone.utc
    )


def test_missing_time_returns_none():
    assert parse_kickoff_utc("2026-06-11", "") is None


def test_garbage_returns_none():
    assert parse_kickoff_utc("2026-06-11", "TBD") is None
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python -m pytest tests/test_kickoff.py -q`
Expected: FAIL（`ModuleNotFoundError: No module named 'wc.kickoff'`）

- [ ] **Step 3: 最小実装**

`wc/kickoff.py`:
```python
"""openfootball の "13:00 UTC-6" 形式の時刻を UTC aware datetime に変換する。"""
import re
from datetime import datetime, timedelta, timezone

_PATTERN = re.compile(r"^\s*(\d{1,2}):(\d{2})\s+UTC([+-]\d{1,2})\s*$")


def parse_kickoff_utc(date_str, time_str):
    """date_str(YYYY-MM-DD) と time_str("HH:MM UTC±N") から UTC datetime を返す。

    解析できない場合は None。
    """
    if not time_str:
        return None
    m = _PATTERN.match(time_str)
    if not m:
        return None
    hour, minute, offset = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        y, mo, d = (int(x) for x in date_str.split("-"))
        local_naive = datetime(y, mo, d, hour, minute)
    except (ValueError, AttributeError):
        return None
    # UTC = ローカル - オフセット時間（UTC-6 なら +6h して UTC へ）
    utc = local_naive - timedelta(hours=offset)
    return utc.replace(tzinfo=timezone.utc)
```

- [ ] **Step 4: テストが通ることを確認**

Run: `python -m pytest tests/test_kickoff.py -q`
Expected: PASS（5 passed）

- [ ] **Step 5: コミット**

```bash
git add wc/kickoff.py tests/test_kickoff.py
git commit -m "feat: キックオフ時刻のUTC変換を追加"
```

---

### Task 4: openfootballパーサー（グループ・チーム・試合・構造組み立て）

**Files:**
- Create: `wc/openfootball.py`
- Test: `tests/test_openfootball.py`

**Interfaces:**
- Consumes: `wc.kickoff.parse_kickoff_utc`
- Produces（すべて純粋関数。入力はJSON文字列、出力はJSON化可能なdict/list）:
  - `parse_groups(text: str) -> list[dict]` → `[{"name":"Group A","teams":[...]}]`
  - `parse_teams(text: str) -> list[dict]` → `[{"name","fifa_code","flag_icon","group","confed","continent"}]`
  - `parse_matches(text: str) -> list[dict]` → 各試合dict（下記スキーマ）
  - `build_structure(wc_text, groups_text, teams_text) -> dict` → `{"name","groups","teams","matches"}`（`generated_at` は付けない＝呼び出し側が注入）

試合dictスキーマ:
```python
{
  "round": "Matchday 1",
  "stage": "group",            # "group" | "knockout"
  "group": "Group A",          # ノックアウトは None
  "date": "2026-06-11",
  "time_local": "13:00 UTC-6",
  "kickoff_utc": "2026-06-11T19:00:00+00:00",  # 解析不能なら None
  "team1": "Mexico", "team2": "South Africa",
  "played": True,              # score.ft があれば True
  "score": {"ft": [2, 0], "ht": [1, 0]},        # 未消化は None
  "goals1": [{"name": "Julián Quiñones", "minute": "9", "penalty": False, "owngoal": False}],
  "goals2": [],
  "ground": "Mexico City",
}
```

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_openfootball.py`:
```python
from wc.openfootball import (
    parse_groups, parse_teams, parse_matches, build_structure,
)

GROUPS = '{"name":"WC","groups":[{"name":"Group A","teams":["Mexico","South Africa"]}]}'
TEAMS = (
    '[{"name":"Mexico","continent":"North America","flag_icon":"\\ud83c\\uddf2\\ud83c\\uddfd",'
    '"fifa_code":"MEX","group":"A","confed":"CONCACAF"}]'
)
MATCHES = (
    '{"name":"WC","matches":['
    '{"round":"Matchday 1","date":"2026-06-11","time":"13:00 UTC-6",'
    '"team1":"Mexico","team2":"South Africa","score":{"ft":[2,0],"ht":[1,0]},'
    '"goals1":[{"name":"Quiñones","minute":"9"},{"name":"Jiménez","minute":"67","penalty":true}],'
    '"goals2":[],"group":"Group A","ground":"Mexico City"},'
    '{"round":"Final","date":"2026-07-19","time":"15:00 UTC-4",'
    '"team1":"Brazil","team2":"Germany","goals1":[],"goals2":[],"ground":"New York"}'
    ']}'
)


def test_parse_groups():
    assert parse_groups(GROUPS) == [
        {"name": "Group A", "teams": ["Mexico", "South Africa"]}
    ]


def test_parse_teams_keeps_key_fields():
    t = parse_teams(TEAMS)[0]
    assert t["name"] == "Mexico"
    assert t["fifa_code"] == "MEX"
    assert t["group"] == "A"
    assert t["confed"] == "CONCACAF"


def test_parse_matches_group_played():
    m = parse_matches(MATCHES)[0]
    assert m["stage"] == "group"
    assert m["group"] == "Group A"
    assert m["played"] is True
    assert m["score"]["ft"] == [2, 0]
    assert m["kickoff_utc"] == "2026-06-11T19:00:00+00:00"
    assert m["goals1"][1]["penalty"] is True
    assert m["goals1"][0]["penalty"] is False


def test_parse_matches_knockout_unplayed():
    m = parse_matches(MATCHES)[1]
    assert m["stage"] == "knockout"
    assert m["group"] is None
    assert m["played"] is False
    assert m["score"] is None


def test_build_structure_combines_all():
    s = build_structure(MATCHES, GROUPS, TEAMS)
    assert s["name"]
    assert len(s["groups"]) == 1
    assert len(s["teams"]) == 1
    assert len(s["matches"]) == 2
    assert "generated_at" not in s  # 呼び出し側が注入する
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python -m pytest tests/test_openfootball.py -q`
Expected: FAIL（`ModuleNotFoundError: No module named 'wc.openfootball'`）

- [ ] **Step 3: 最小実装**

`wc/openfootball.py`:
```python
"""openfootball/worldcup.json (2026) のJSONを内部スキーマへ変換する純粋パーサー。"""
import json

from wc.kickoff import parse_kickoff_utc

# グループ戦以外のラウンド名（ノックアウト判定用）
_KNOCKOUT_ROUNDS = {
    "Round of 32", "Round of 16", "Quarter-final",
    "Semi-final", "Match for third place", "Final",
}


def parse_groups(text):
    data = json.loads(text)
    return [
        {"name": g["name"], "teams": list(g.get("teams", []))}
        for g in data.get("groups", [])
    ]


def parse_teams(text):
    data = json.loads(text)
    out = []
    for t in data:
        out.append({
            "name": t["name"],
            "fifa_code": t.get("fifa_code", ""),
            "flag_icon": t.get("flag_icon", ""),
            "group": t.get("group", ""),
            "confed": t.get("confed", ""),
            "continent": t.get("continent", ""),
        })
    return out


def _parse_goals(raw):
    out = []
    for g in raw or []:
        out.append({
            "name": g.get("name", ""),
            "minute": str(g.get("minute", "")),
            "penalty": bool(g.get("penalty", False)),
            "owngoal": bool(g.get("owngoal", False)),
        })
    return out


def parse_matches(text):
    data = json.loads(text)
    out = []
    for m in data.get("matches", []):
        round_name = m.get("round", "")
        stage = "knockout" if round_name in _KNOCKOUT_ROUNDS else "group"
        score = m.get("score")
        played = bool(score and score.get("ft"))
        ko = parse_kickoff_utc(m.get("date", ""), m.get("time", ""))
        out.append({
            "round": round_name,
            "stage": stage,
            "group": m.get("group") if stage == "group" else None,
            "date": m.get("date", ""),
            "time_local": m.get("time", ""),
            "kickoff_utc": ko.isoformat() if ko else None,
            "team1": m.get("team1", ""),
            "team2": m.get("team2", ""),
            "played": played,
            "score": score if played else None,
            "goals1": _parse_goals(m.get("goals1")),
            "goals2": _parse_goals(m.get("goals2")),
            "ground": m.get("ground", ""),
        })
    return out


def build_structure(wc_text, groups_text, teams_text):
    """3ファイルのテキストから構造化dictを組み立てる（generated_atは付けない）。"""
    matches = parse_matches(wc_text)
    name = json.loads(wc_text).get("name", "World Cup 2026")
    return {
        "name": name,
        "groups": parse_groups(groups_text),
        "teams": parse_teams(teams_text),
        "matches": matches,
    }
```

- [ ] **Step 4: テストが通ることを確認**

Run: `python -m pytest tests/test_openfootball.py -q`
Expected: PASS（5 passed）

- [ ] **Step 5: コミット**

```bash
git add wc/openfootball.py tests/test_openfootball.py
git commit -m "feat: openfootballパーサー（グループ/チーム/試合/構造）を追加"
```

---

### Task 5: グループ順位表の集計

**Files:**
- Create: `wc/standings.py`
- Test: `tests/test_standings.py`

**Interfaces:**
- Consumes: `parse_matches` 形式の試合dictリスト
- Produces:
  - `compute_standings(matches: list[dict]) -> dict[str, list[dict]]`
    - キー = グループ名（`"Group A"`）、値 = 順位行リスト（順位順）。
    - 行: `{"pos","team","played","win","draw","loss","gf","ga","gd","points"}`
    - 対象は `stage=="group"` かつ `played==True` の試合のみ。
    - 並び順タイブレーク: 勝点降順 → 得失点差降順 → 総得点降順 → チーム名昇順（決定的）。
    - ※ 直接対決（head-to-head）等の上位タイブレークはプラン外（将来拡張）。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_standings.py`:
```python
from wc.standings import compute_standings


def _m(group, t1, t2, ft, played=True, stage="group"):
    return {
        "stage": stage, "group": group, "team1": t1, "team2": t2,
        "played": played, "score": {"ft": ft} if played else None,
    }


def test_basic_points_and_order():
    matches = [
        _m("Group A", "Mexico", "Korea", [2, 0]),     # Mexico勝
        _m("Group A", "Mexico", "Czech", [1, 0]),     # Mexico勝
        _m("Group A", "Korea", "Czech", [1, 1]),      # 引分
    ]
    table = compute_standings(matches)["Group A"]
    assert [r["team"] for r in table] == ["Mexico", "Korea", "Czech"]
    assert table[0]["points"] == 6
    assert table[0]["pos"] == 1
    assert table[0]["gd"] == 3
    assert table[1]["points"] == 1   # Korea: 引分1
    assert table[2]["points"] == 1   # Czech: 引分1


def test_goal_difference_tiebreak():
    matches = [
        _m("Group B", "A", "X", [5, 0]),  # A: +5
        _m("Group B", "B", "Y", [1, 0]),  # B: +1
        _m("Group B", "A", "B", [0, 0]),  # 引分、両者+0
    ]
    table = compute_standings(matches)["Group B"]
    # A と B は勝点4で並ぶ→ 得失点差で A(+5) が上
    assert table[0]["team"] == "A"
    assert table[0]["gd"] == 5


def test_unplayed_and_knockout_ignored():
    matches = [
        _m("Group C", "A", "B", [1, 0]),
        _m("Group C", "A", "C", [9, 0], played=False),     # 未消化→無視
        _m(None, "A", "D", [3, 0], stage="knockout"),      # KO→無視
    ]
    table = compute_standings(matches)["Group C"]
    a = next(r for r in table if r["team"] == "A")
    assert a["played"] == 1
    assert a["gf"] == 1  # 未消化9点は加算されない
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python -m pytest tests/test_standings.py -q`
Expected: FAIL（`ModuleNotFoundError: No module named 'wc.standings'`）

- [ ] **Step 3: 最小実装**

`wc/standings.py`:
```python
"""グループ別の順位表を試合結果から集計する。"""


def _blank(team):
    return {
        "team": team, "played": 0, "win": 0, "draw": 0, "loss": 0,
        "gf": 0, "ga": 0, "gd": 0, "points": 0,
    }


def compute_standings(matches):
    """グループ名→順位行リスト（順位順）を返す。

    対象は stage=="group" かつ played==True の試合のみ。
    タイブレーク: 勝点 → 得失点差 → 総得点 → チーム名。
    """
    groups = {}
    for m in matches:
        if m.get("stage") != "group" or not m.get("played"):
            continue
        g = m.get("group")
        if not g:
            continue
        gf1, gf2 = m["score"]["ft"][0], m["score"]["ft"][1]
        rows = groups.setdefault(g, {})
        r1 = rows.setdefault(m["team1"], _blank(m["team1"]))
        r2 = rows.setdefault(m["team2"], _blank(m["team2"]))
        for r, gf, ga in ((r1, gf1, gf2), (r2, gf2, gf1)):
            r["played"] += 1
            r["gf"] += gf
            r["ga"] += ga
            r["gd"] = r["gf"] - r["ga"]
            if gf > ga:
                r["win"] += 1
                r["points"] += 3
            elif gf == ga:
                r["draw"] += 1
                r["points"] += 1
            else:
                r["loss"] += 1

    result = {}
    for g, rows in groups.items():
        ordered = sorted(
            rows.values(),
            key=lambda r: (-r["points"], -r["gd"], -r["gf"], r["team"]),
        )
        for i, r in enumerate(ordered, start=1):
            r["pos"] = i
        result[g] = ordered
    return result
```

- [ ] **Step 4: テストが通ることを確認**

Run: `python -m pytest tests/test_standings.py -q`
Expected: PASS（3 passed）

- [ ] **Step 5: コミット**

```bash
git add wc/standings.py tests/test_standings.py
git commit -m "feat: グループ順位表の集計を追加"
```

---

### Task 6: 得点王ランキングの集計

**Files:**
- Create: `wc/scorers.py`
- Test: `tests/test_scorers.py`

**Interfaces:**
- Consumes: `parse_matches` 形式の試合dictリスト
- Produces:
  - `compute_scorers(matches: list[dict]) -> list[dict]`
    - 行: `{"name","team","goals","penalties"}`、得点数降順 → PK数昇順 → 名前昇順。
    - `goals1` は `team1`、`goals2` は `team2` に帰属。
    - オウンゴール（`owngoal==True`）は得点王ランキングから除外。
    - 対象は `played==True` の試合（グループ・ノックアウト両方）。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_scorers.py`:
```python
from wc.scorers import compute_scorers


def _goal(name, penalty=False, owngoal=False):
    return {"name": name, "minute": "10", "penalty": penalty, "owngoal": owngoal}


def test_aggregates_and_orders():
    matches = [
        {"played": True, "team1": "Mexico", "team2": "Korea",
         "goals1": [_goal("Quiñones"), _goal("Quiñones")], "goals2": [_goal("Son")]},
        {"played": True, "team1": "Mexico", "team2": "Czech",
         "goals1": [_goal("Quiñones")], "goals2": []},
    ]
    table = compute_scorers(matches)
    assert table[0] == {"name": "Quiñones", "team": "Mexico", "goals": 3, "penalties": 0}
    assert table[1]["name"] == "Son"


def test_penalties_counted_separately():
    matches = [{"played": True, "team1": "A", "team2": "B",
                "goals1": [_goal("P", penalty=True), _goal("P")], "goals2": []}]
    row = compute_scorers(matches)[0]
    assert row["goals"] == 2
    assert row["penalties"] == 1


def test_owngoal_excluded():
    matches = [{"played": True, "team1": "A", "team2": "B",
                "goals1": [_goal("OG", owngoal=True)], "goals2": []}]
    assert compute_scorers(matches) == []


def test_unplayed_ignored():
    matches = [{"played": False, "team1": "A", "team2": "B",
                "goals1": [_goal("X")], "goals2": []}]
    assert compute_scorers(matches) == []
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python -m pytest tests/test_scorers.py -q`
Expected: FAIL（`ModuleNotFoundError: No module named 'wc.scorers'`）

- [ ] **Step 3: 最小実装**

`wc/scorers.py`:
```python
"""得点王ランキングを試合の得点者データから集計する。"""


def compute_scorers(matches):
    """選手別の得点・PK数を集計し、得点数降順で返す。

    オウンゴールは除外。goals1→team1、goals2→team2 に帰属。
    """
    tally = {}  # (name, team) -> {"goals","penalties"}
    for m in matches:
        if not m.get("played"):
            continue
        for goals, team in (
            (m.get("goals1"), m.get("team1")),
            (m.get("goals2"), m.get("team2")),
        ):
            for g in goals or []:
                if g.get("owngoal"):
                    continue
                key = (g.get("name", ""), team)
                row = tally.setdefault(key, {"goals": 0, "penalties": 0})
                row["goals"] += 1
                if g.get("penalty"):
                    row["penalties"] += 1

    out = [
        {"name": name, "team": team, "goals": v["goals"], "penalties": v["penalties"]}
        for (name, team), v in tally.items()
    ]
    out.sort(key=lambda r: (-r["goals"], r["penalties"], r["name"]))
    return out
```

- [ ] **Step 4: テストが通ることを確認**

Run: `python -m pytest tests/test_scorers.py -q`
Expected: PASS（4 passed）

- [ ] **Step 5: コミット**

```bash
git add wc/scorers.py tests/test_scorers.py
git commit -m "feat: 得点王ランキングの集計を追加"
```

---

### Task 7: スケジュールゲート（試合時間帯の判定）

**Files:**
- Create: `wc/schedule_gate.py`
- Test: `tests/test_schedule_gate.py`

**Interfaces:**
- Consumes: `parse_matches` 形式の試合dictリスト（`kickoff_utc` フィールド使用）
- Produces:
  - `is_in_match_window(matches: list[dict], now_utc: datetime, post_hours: int = 3) -> bool`
    - いずれかの試合で `kickoff_utc <= now_utc <= kickoff_utc + post_hours時間` なら `True`。
    - `kickoff_utc` が `None` の試合は無視。
  - `main(argv=None) -> int`：`data/structure.json` を読み、現在UTC時刻で判定。窓内なら `0` を返し `RUN` を出力、窓外なら `1` を返し `SKIP` を出力（GitHub Actionsの条件分岐用）。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_schedule_gate.py`:
```python
from datetime import datetime, timezone

from wc.schedule_gate import is_in_match_window


def _m(iso):
    return {"kickoff_utc": iso}


MATCHES = [_m("2026-06-11T19:00:00+00:00"), _m(None)]


def test_inside_window_at_kickoff():
    now = datetime(2026, 6, 11, 19, 0, tzinfo=timezone.utc)
    assert is_in_match_window(MATCHES, now) is True


def test_inside_window_two_hours_in():
    now = datetime(2026, 6, 11, 21, 0, tzinfo=timezone.utc)
    assert is_in_match_window(MATCHES, now) is True


def test_after_window():
    now = datetime(2026, 6, 11, 22, 30, tzinfo=timezone.utc)
    assert is_in_match_window(MATCHES, now) is False


def test_before_kickoff():
    now = datetime(2026, 6, 11, 18, 0, tzinfo=timezone.utc)
    assert is_in_match_window(MATCHES, now) is False


def test_none_kickoff_ignored():
    now = datetime(2026, 6, 11, 19, 0, tzinfo=timezone.utc)
    assert is_in_match_window([_m(None)], now) is False
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python -m pytest tests/test_schedule_gate.py -q`
Expected: FAIL（`ModuleNotFoundError: No module named 'wc.schedule_gate'`）

- [ ] **Step 3: 最小実装**

`wc/schedule_gate.py`:
```python
"""試合時間帯（kickoff〜+post_hours）かを判定し、CLIで終了コードを返す。"""
import sys
from datetime import datetime, timedelta, timezone

from wc.atomic_io import read_json_or_none


def is_in_match_window(matches, now_utc, post_hours=3):
    """いずれかの試合の [kickoff, kickoff+post_hours] に now_utc が入れば True。"""
    window = timedelta(hours=post_hours)
    for m in matches:
        iso = m.get("kickoff_utc")
        if not iso:
            continue
        ko = datetime.fromisoformat(iso)
        if ko <= now_utc <= ko + window:
            return True
    return False


def main(argv=None):
    structure = read_json_or_none("data/structure.json")
    if not structure:
        print("SKIP (no structure.json)")
        return 1
    now = datetime.now(timezone.utc)
    if is_in_match_window(structure.get("matches", []), now):
        print("RUN")
        return 0
    print("SKIP")
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: テストが通ることを確認**

Run: `python -m pytest tests/test_schedule_gate.py -q`
Expected: PASS（5 passed）

- [ ] **Step 5: コミット**

```bash
git add wc/schedule_gate.py tests/test_schedule_gate.py
git commit -m "feat: 試合時間帯を判定するスケジュールゲートを追加"
```

---

### Task 8: 取得層（curl）とオーケストレータ

**Files:**
- Create: `wc/fetch.py`
- Create: `wc/update_data.py`
- Test: `tests/test_fetch.py`
- Test: `tests/test_update_data.py`

**Interfaces:**
- Consumes: `wc.fetch.fetch_text`, `wc.openfootball.build_structure`, `wc.standings.compute_standings`, `wc.scorers.compute_scorers`, `wc.atomic_io.write_json_atomic`
- Produces:
  - `wc/fetch.py`: `fetch_text(url: str, timeout: int = 30) -> str`（curlで本文取得。空 or 非ゼロ終了で `FetchError`）。例外クラス `FetchError(Exception)`。
  - `wc/update_data.py`:
    - `BASE_URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026"`
    - `build_outputs(wc_text, groups_text, teams_text, now_iso) -> tuple[dict, dict]`（純粋関数：structure dict と rankings dict を返す）
    - `main(fetcher=fetch_text, out_dir="data", now_iso=None) -> int`：取得→生成→`data/structure.json`・`data/rankings.json` 書き込み。取得失敗時はファイルに触れず `1` を返す。成功時 `0`。

`main` の `fetcher` 引数で取得関数を差し替え可能にし、テストはネットワークなしで実行する。

- [ ] **Step 1: 失敗するテストを書く（fetch）**

`tests/test_fetch.py`:
```python
import pytest

from wc.fetch import fetch_text, FetchError


def test_fetch_text_returns_stdout(monkeypatch):
    class FakeProc:
        returncode = 0
        stdout = '{"ok": 1}'
        stderr = ""

    monkeypatch.setattr("wc.fetch.subprocess.run", lambda *a, **k: FakeProc())
    assert fetch_text("https://example.com/x.json") == '{"ok": 1}'


def test_fetch_text_raises_on_nonzero(monkeypatch):
    class FakeProc:
        returncode = 7
        stdout = ""
        stderr = "boom"

    monkeypatch.setattr("wc.fetch.subprocess.run", lambda *a, **k: FakeProc())
    with pytest.raises(FetchError):
        fetch_text("https://example.com/x.json")


def test_fetch_text_raises_on_empty(monkeypatch):
    class FakeProc:
        returncode = 0
        stdout = "   "
        stderr = ""

    monkeypatch.setattr("wc.fetch.subprocess.run", lambda *a, **k: FakeProc())
    with pytest.raises(FetchError):
        fetch_text("https://example.com/x.json")
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python -m pytest tests/test_fetch.py -q`
Expected: FAIL（`ModuleNotFoundError: No module named 'wc.fetch'`）

- [ ] **Step 3: 最小実装（fetch）**

`wc/fetch.py`:
```python
"""curl サブプロセスでURL本文を取得する（macOSのSSL証明書エラー回避のため）。"""
import subprocess


class FetchError(Exception):
    """取得失敗（非ゼロ終了・空応答・タイムアウト）。"""


def fetch_text(url, timeout=30):
    """curl -sL でURL本文を返す。失敗時は FetchError。"""
    try:
        proc = subprocess.run(
            ["curl", "-sL", "--fail", "--max-time", str(timeout), url],
            capture_output=True, text=True, timeout=timeout + 5,
        )
    except subprocess.TimeoutExpired as e:
        raise FetchError(f"timeout: {url}") from e
    if proc.returncode != 0:
        raise FetchError(f"curl exit {proc.returncode}: {url} {proc.stderr.strip()}")
    if not proc.stdout or not proc.stdout.strip():
        raise FetchError(f"empty response: {url}")
    return proc.stdout
```

- [ ] **Step 4: テストが通ることを確認**

Run: `python -m pytest tests/test_fetch.py -q`
Expected: PASS（3 passed）

- [ ] **Step 5: 失敗するテストを書く（update_data）**

`tests/test_update_data.py`:
```python
import json
from pathlib import Path

import pytest

from wc.update_data import build_outputs, main
from wc.fetch import FetchError

GROUPS = '{"name":"WC","groups":[{"name":"Group A","teams":["Mexico","Korea"]}]}'
TEAMS = '[{"name":"Mexico","fifa_code":"MEX","group":"A","confed":"CONCACAF","flag_icon":"x","continent":"NA"}]'
MATCHES = (
    '{"name":"WC","matches":['
    '{"round":"Matchday 1","date":"2026-06-11","time":"13:00 UTC-6",'
    '"team1":"Mexico","team2":"Korea","score":{"ft":[2,0],"ht":[1,0]},'
    '"goals1":[{"name":"Quiñones","minute":"9"}],"goals2":[],"group":"Group A","ground":"X"}'
    ']}'
)


def test_build_outputs_shapes():
    structure, rankings = build_outputs(MATCHES, GROUPS, TEAMS, "2026-06-30T00:00:00+00:00")
    assert structure["generated_at"] == "2026-06-30T00:00:00+00:00"
    assert len(structure["matches"]) == 1
    assert rankings["standings"]["Group A"][0]["team"] == "Mexico"
    assert rankings["scorers"][0]["name"] == "Quiñones"


def _fake_fetcher(url):
    if url.endswith("worldcup.json"):
        return MATCHES
    if url.endswith("worldcup.groups.json"):
        return GROUPS
    if url.endswith("worldcup.teams.json"):
        return TEAMS
    raise AssertionError(url)


def test_main_writes_files(tmp_path):
    rc = main(fetcher=_fake_fetcher, out_dir=str(tmp_path), now_iso="2026-06-30T00:00:00+00:00")
    assert rc == 0
    structure = json.loads((tmp_path / "structure.json").read_text(encoding="utf-8"))
    rankings = json.loads((tmp_path / "rankings.json").read_text(encoding="utf-8"))
    assert structure["matches"][0]["team1"] == "Mexico"
    assert rankings["scorers"][0]["goals"] == 1


def test_main_preserves_files_on_fetch_error(tmp_path):
    # 既存の正常ファイルを置いておく
    (tmp_path / "structure.json").write_text('{"old": true}', encoding="utf-8")

    def broken(url):
        raise FetchError("network down")

    rc = main(fetcher=broken, out_dir=str(tmp_path), now_iso="2026-06-30T00:00:00+00:00")
    assert rc == 1
    # 既存ファイルは壊されない
    assert json.loads((tmp_path / "structure.json").read_text(encoding="utf-8")) == {"old": True}
```

- [ ] **Step 6: テストが失敗することを確認**

Run: `python -m pytest tests/test_update_data.py -q`
Expected: FAIL（`ModuleNotFoundError: No module named 'wc.update_data'`）

- [ ] **Step 7: 最小実装（update_data）**

`wc/update_data.py`:
```python
"""openfootballから取得し data/structure.json と data/rankings.json を生成する。"""
import sys
from datetime import datetime, timezone
from pathlib import Path

from wc.fetch import fetch_text, FetchError
from wc.openfootball import build_structure
from wc.standings import compute_standings
from wc.scorers import compute_scorers
from wc.atomic_io import write_json_atomic

BASE_URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026"


def build_outputs(wc_text, groups_text, teams_text, now_iso):
    """取得テキストから structure dict と rankings dict を生成する（純粋関数）。"""
    structure = build_structure(wc_text, groups_text, teams_text)
    structure["generated_at"] = now_iso
    matches = structure["matches"]
    rankings = {
        "generated_at": now_iso,
        "standings": compute_standings(matches),
        "scorers": compute_scorers(matches),
    }
    return structure, rankings


def main(fetcher=fetch_text, out_dir="data", now_iso=None):
    """取得→生成→書き込み。取得失敗時は既存ファイルを保持して 1 を返す。"""
    if now_iso is None:
        now_iso = datetime.now(timezone.utc).isoformat()
    try:
        wc_text = fetcher(f"{BASE_URL}/worldcup.json")
        groups_text = fetcher(f"{BASE_URL}/worldcup.groups.json")
        teams_text = fetcher(f"{BASE_URL}/worldcup.teams.json")
    except FetchError as e:
        print(f"取得失敗のため既存データを保持します: {e}", file=sys.stderr)
        return 1

    structure, rankings = build_outputs(wc_text, groups_text, teams_text, now_iso)
    out = Path(out_dir)
    write_json_atomic(out / "structure.json", structure)
    write_json_atomic(out / "rankings.json", rankings)
    print(f"書き込み完了: {out}/structure.json, {out}/rankings.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 8: テストが通ることを確認**

Run: `python -m pytest tests/test_update_data.py -q`
Expected: PASS（3 passed）

- [ ] **Step 9: 実データで疎通確認（手動・ネットワーク使用）**

Run: `cd /Users/member1/agents/WorldCupWebsite && python -m wc.update_data`
Expected: `書き込み完了: data/structure.json, data/rankings.json` と表示され、`data/structure.json`（matches多数）と `data/rankings.json`（standings 12グループ・scorers）が生成される。

- [ ] **Step 10: 全テスト実行**

Run: `python -m pytest -q`
Expected: PASS（全テスト green）

- [ ] **Step 11: コミット**

```bash
git add wc/fetch.py wc/update_data.py tests/test_fetch.py tests/test_update_data.py
git commit -m "feat: 取得層とデータ生成オーケストレータを追加"
```

> 注: `data/structure.json`・`data/rankings.json` は生成物。サイト（プラン2）が参照するためコミット対象に含めるが、初回は実データ生成後に明示パスで `git add data/structure.json data/rankings.json` してコミットする。実取引先データのような機密ではない（公開大会データ）。

---

## Self-Review（spec照合）

- **データ方式（openfootball中心・無料）**: Task 4・8で実装 ✅
- **構造化JSON（グループ/チーム/試合/スコア/得点者）**: Task 4 `build_structure` ✅
- **順位表＋タイブレーク**: Task 5 ✅（h2hは将来拡張と明記）
- **得点王ランキング**: Task 6 ✅
- **アシスト/警告等**: openfootball worldcup.jsonに該当データが無いため本プラン対象外。spec「無データ項目は自動非表示」に従い、プラン2のサイト側で非表示にする（プラン3でfootball-data補完を検討）。← spec整合のため明記。
- **スケジュールゲート（試合時間帯のみ）**: Task 7 ✅
- **アトミック書き込み＋前回値保持**: Task 2・Task 8（取得失敗時保持）✅
- **TDD/日本語/curl/git add明示パス/safe-init-commit**: Global Constraints・各タスクで遵守 ✅
- **プラン外（後続プラン）**: 静的サイト生成（プラン2）、YouTube・ニュース・football-data鮮度補完・GitHub Actions自動化（プラン3）。

プレースホルダなし。型整合（`matches` dictスキーマ／`compute_standings`・`compute_scorers` のキー名）はタスク間で一致。
