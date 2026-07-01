"""The Odds API (the-odds-api.com) v4 からブックメーカーのオッズを取得。

用途は「勝敗予想の材料」。h2h(1X2)の平均オッズと勝率換算(実装確率)を表示する。
※ あくまで参考情報であり賭博の推奨・斡旋ではない。免責はレンダリング側で表示。
無料枠は500クレジット/月・未消化(これから行う)試合のみ。鍵が無ければスキップ。
"""
import json
import subprocess
import sys
from datetime import datetime, timezone

from wc.fetch import FetchError
from wc.atomic_io import read_json_or_none, write_json_atomic
from wc.matchid import match_key

HOST = "https://api.the-odds-api.com/v4"
SPORT_KEY = "soccer_fifa_world_cup"

# The Odds API の表記 → openfootball 表記（既知差分のみ）
ODDS_TEAM_ALIASES = {
    "Korea Republic": "South Korea",
    "IR Iran": "Iran",
    "Czechia": "Czech Republic",
    "Cote d'Ivoire": "Ivory Coast",
    "Côte d'Ivoire": "Ivory Coast",
    "Turkiye": "Turkey",
    "Türkiye": "Turkey",
    "United States": "USA",
}


def normalize_odds_name(name):
    return ODDS_TEAM_ALIASES.get(name, name)


def build_odds_url(api_key, regions="uk", markets="h2h"):
    return (f"{HOST}/sports/{SPORT_KEY}/odds?apiKey={api_key}"
            f"&regions={regions}&markets={markets}&oddsFormat=decimal")


def fetch_odds(url, timeout=30):
    """curlでオッズを取得（エラーボディも取得するため --fail は付けない）。"""
    try:
        proc = subprocess.run(
            ["curl", "-sL", "--max-time", str(timeout), url],
            capture_output=True, text=True, timeout=timeout + 5,
        )
    except subprocess.TimeoutExpired as e:
        raise FetchError(f"timeout: odds") from e
    if proc.returncode != 0:
        raise FetchError(f"curl exit {proc.returncode}: {proc.stderr.strip()}")
    if not proc.stdout or not proc.stdout.strip():
        raise FetchError("empty response: odds")
    return proc.stdout


def implied_probs(o_home, o_draw, o_away):
    """デシマルオッズ3つから、マージン除去済みの勝率(%)を返す。"""
    raw = {}
    for k, o in (("home", o_home), ("draw", o_draw), ("away", o_away)):
        raw[k] = (1.0 / o) if o else 0.0
    tot = sum(raw.values())
    if tot <= 0:
        return {"home": 0, "draw": 0, "away": 0}
    return {k: round(v / tot * 100) for k, v in raw.items()}


def parse_odds(json_text):
    """The Odds API レスポンス → [{home,away,date,books,odds,probs}]。エラー/壊れは []。"""
    try:
        data = json.loads(json_text)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(data, list):  # エラーは {"message": ...} オブジェクト
        return []
    out = []
    for ev in data:
        home = ev.get("home_team", "")
        away = ev.get("away_team", "")
        prices = {"home": [], "draw": [], "away": []}
        for bk in ev.get("bookmakers", []):
            for mk in bk.get("markets", []):
                if mk.get("key") != "h2h":
                    continue
                for oc in mk.get("outcomes", []):
                    nm, pr = oc.get("name"), oc.get("price")
                    if pr is None:
                        continue
                    if nm == home:
                        prices["home"].append(pr)
                    elif nm == away:
                        prices["away"].append(pr)
                    elif nm == "Draw":
                        prices["draw"].append(pr)
        if not any(prices.values()):
            continue
        avg = {k: (sum(v) / len(v) if v else None) for k, v in prices.items()}
        probs = implied_probs(avg["home"], avg["draw"], avg["away"])
        out.append({
            "home": home,
            "away": away,
            "date": (ev.get("commence_time") or "")[:10],
            "books": max(len(v) for v in prices.values()),
            "odds": {k: (round(avg[k], 2) if avg[k] else None) for k in avg},
            "probs": probs,
        })
    return out


def _odds_index(events):
    """frozenset(正規化2チーム名) → オッズ情報（未消化のペアは一意）。"""
    idx = {}
    for e in events:
        key = frozenset((normalize_odds_name(e["home"]), normalize_odds_name(e["away"])))
        idx[key] = e
    return idx


def main(data_dir="data", api_key=None, fetcher=fetch_odds, now_iso=None):
    """鍵が無ければ SKIP。あれば未消化試合のオッズを取得し data/odds.json に保存。"""
    if api_key is None:
        import os
        api_key = os.environ.get("ODDS_API_KEY", "")
    if not api_key:
        print("SKIP: ODDS_API_KEY が未設定のためオッズ取得を省略します。")
        return 0
    structure = read_json_or_none(f"{data_dir}/structure.json")
    if not structure:
        print("SKIP: structure.json が無いためオッズ取得を省略します。", file=sys.stderr)
        return 1
    if now_iso is None:
        now_iso = datetime.now(timezone.utc).isoformat()

    try:
        raw = fetcher(build_odds_url(api_key))
    except FetchError as e:
        print(f"オッズ取得失敗（既存保持）: {e}", file=sys.stderr)
        return 0
    # エラーオブジェクトなら既存保持で終了
    try:
        peek = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        peek = None
    if isinstance(peek, dict):
        print(f"Odds APIエラー（既存保持）: {peek.get('message')}", file=sys.stderr)
        return 0

    events = parse_odds(raw)
    idx = _odds_index(events)
    print(f"[診断] odds events={len(events)}")

    # 既存を保持（消化済み試合のオッズは“キックオフ直前の凍結値”として残す）
    result = dict((read_json_or_none(f"{data_dir}/odds.json") or {}).get("items", {}))
    updated = 0
    for m in structure.get("matches", []):
        if m.get("played"):  # 消化済みは更新しない＝既存の凍結値を保持
            continue
        e = idx.get(frozenset((m.get("team1", ""), m.get("team2", ""))))
        if not e:
            continue
        # 未消化は毎回最新オッズで上書き（＝最後に取れた値が“直前オッズ”になる）
        result[match_key(m)] = {
            "home": m.get("team1", ""), "away": m.get("team2", ""),
            "odds": e["odds"], "probs": e["probs"], "books": e["books"],
            "captured": now_iso,
        }
        updated += 1
    write_json_atomic(f"{data_dir}/odds.json", {"generated_at": now_iso, "items": result})
    print(f"オッズ 更新{updated} / 保持含め計{len(result)} 試合分を書き込みました: {data_dir}/odds.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
