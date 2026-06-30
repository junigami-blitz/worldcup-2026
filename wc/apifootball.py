"""API-Football (api-sports.io) からスタメン・選手スタッツ・チームスタッツを取得。

無料枠100req/日。試合終了後に1試合分を取得してキャッシュ（data/lineups.json）。
鍵(API_FOOTBALL_KEY)が無ければスキップ。レスポンスは公式v3スキーマ準拠。
チーム名表記が openfootball と異なるためエイリアスで正規化する。
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

from wc.fetch import FetchError
from wc.atomic_io import read_json_or_none, write_json_atomic
from wc.matchid import match_key

HOST = "https://v3.football.api-sports.io"
WORLD_CUP_LEAGUE_ID = 1  # FIFA World Cup
DEFAULT_MAX_FIXTURES = 12  # 1試合最大3リクエスト→100/日枠を考慮した1回の上限

# API-Football の表記 → openfootball の表記（既知差分のみ・未知はそのまま）
AF_TEAM_ALIASES = {
    "Korea Republic": "South Korea",
    "IR Iran": "Iran",
    "Czechia": "Czech Republic",
    "Côte d'Ivoire": "Ivory Coast",
    "Cote D'Ivoire": "Ivory Coast",
    "Cape Verde Islands": "Cape Verde",
    "Türkiye": "Turkey",
    "USA": "USA",
}


def normalize_af_name(name):
    return AF_TEAM_ALIASES.get(name, name)


def build_fixtures_url(season, league=WORLD_CUP_LEAGUE_ID):
    return f"{HOST}/fixtures?league={league}&season={season}"


def build_lineups_url(fixture_id):
    return f"{HOST}/fixtures/lineups?fixture={fixture_id}"


def build_players_url(fixture_id):
    return f"{HOST}/fixtures/players?fixture={fixture_id}"


def build_stats_url(fixture_id):
    return f"{HOST}/fixtures/statistics?fixture={fixture_id}"


def fetch_af(url, api_key, timeout=30):
    """x-apisports-key ヘッダ付きで API-Football を取得。失敗時 FetchError。"""
    try:
        proc = subprocess.run(
            ["curl", "-sL", "--max-time", str(timeout),
             "-H", f"x-apisports-key: {api_key}", url],
            capture_output=True, text=True, timeout=timeout + 5,
        )
    except subprocess.TimeoutExpired as e:
        raise FetchError(f"timeout: {url}") from e
    if proc.returncode != 0:
        raise FetchError(f"curl exit {proc.returncode}: {url} {proc.stderr.strip()}")
    if not proc.stdout or not proc.stdout.strip():
        raise FetchError(f"empty response: {url}")
    return proc.stdout


def _load(json_text):
    try:
        return json.loads(json_text)
    except (json.JSONDecodeError, TypeError):
        return None


def parse_fixtures(json_text):
    """fixtures レスポンス → [{api_id, date, home, away}]（紐づけ用）。"""
    data = _load(json_text)
    if not data:
        return []
    out = []
    for f in data.get("response", []):
        fx = f.get("fixture") or {}
        teams = f.get("teams") or {}
        out.append({
            "api_id": fx.get("id"),
            "date": (fx.get("date") or "")[:10],
            "home": (teams.get("home") or {}).get("name", ""),
            "away": (teams.get("away") or {}).get("name", ""),
        })
    return out


def _player(p):
    pl = p.get("player") or {}
    return {
        "id": pl.get("id"),
        "name": pl.get("name", ""),
        "number": pl.get("number"),
        "pos": pl.get("pos", ""),
        "grid": pl.get("grid"),
    }


def parse_lineups(json_text):
    """lineups レスポンス → [{team,formation,coach,startXI,substitutes}]（2チーム）。"""
    data = _load(json_text)
    if not data:
        return []
    out = []
    for t in data.get("response", []):
        out.append({
            "team": (t.get("team") or {}).get("name", ""),
            "formation": t.get("formation", ""),
            "coach": (t.get("coach") or {}).get("name", ""),
            "startXI": [_player(p) for p in t.get("startXI", [])],
            "substitutes": [_player(p) for p in t.get("substitutes", [])],
        })
    return out


def parse_player_stats(json_text):
    """players レスポンス → [{team, players:[{name,minutes,rating,goals,shots,passes,yellow,red}]}]。"""
    data = _load(json_text)
    if not data:
        return []
    out = []
    for t in data.get("response", []):
        players = []
        for p in t.get("players", []):
            pl = p.get("player") or {}
            st = (p.get("statistics") or [{}])[0]
            games = st.get("games") or {}
            goals = st.get("goals") or {}
            shots = st.get("shots") or {}
            passes = st.get("passes") or {}
            cards = st.get("cards") or {}
            players.append({
                "name": pl.get("name", ""),
                "minutes": games.get("minutes"),
                "rating": games.get("rating"),
                "position": games.get("position", ""),
                "captain": bool(games.get("captain")),
                "substitute": bool(games.get("substitute")),
                "goals": goals.get("total") or 0,
                "assists": goals.get("assists") or 0,
                "shots": shots.get("total") or 0,
                "passes": passes.get("total") or 0,
                "yellow": cards.get("yellow") or 0,
                "red": cards.get("red") or 0,
            })
        out.append({"team": (t.get("team") or {}).get("name", ""), "players": players})
    return out


def parse_team_stats(json_text):
    """statistics レスポンス → [{team, stats:[{type,value}]}]。None値は除外。"""
    data = _load(json_text)
    if not data:
        return []
    out = []
    for t in data.get("response", []):
        stats = [{"type": s.get("type", ""), "value": s.get("value")}
                 for s in t.get("statistics", []) if s.get("value") is not None]
        out.append({"team": (t.get("team") or {}).get("name", ""), "stats": stats})
    return out


def _fixture_index(fixtures):
    """(date, frozenset(正規化チーム名2つ)) → api_id。"""
    idx = {}
    for f in fixtures:
        key = (f["date"], frozenset((normalize_af_name(f["home"]), normalize_af_name(f["away"]))))
        if f.get("api_id"):
            idx[key] = f["api_id"]
    return idx


def main(data_dir="data", api_key=None, fetcher=fetch_af, now_iso=None,
         season=2026, max_fixtures=DEFAULT_MAX_FIXTURES):
    """鍵が無ければ SKIP。鍵があれば終了済み未キャッシュ試合のスタメン等を取得。"""
    if api_key is None:
        api_key = os.environ.get("API_FOOTBALL_KEY", "")
    if not api_key:
        print("SKIP: API_FOOTBALL_KEY が未設定のためスタメン取得を省略します。")
        return 0
    structure = read_json_or_none(f"{data_dir}/structure.json")
    if not structure:
        print("SKIP: structure.json が無いためスタメン取得を省略します。", file=sys.stderr)
        return 1
    if now_iso is None:
        now_iso = datetime.now(timezone.utc).isoformat()

    existing = (read_json_or_none(f"{data_dir}/lineups.json") or {}).get("items", {})

    # fixture 一覧で api_id を紐づけ（1リクエスト）
    try:
        fixtures = parse_fixtures(fetcher(build_fixtures_url(season), api_key))
    except FetchError as e:
        print(f"fixtures取得失敗のためスタメン取得を中止: {e}", file=sys.stderr)
        return 1
    idx = _fixture_index(fixtures)

    result = dict(existing)
    count = 0
    for m in structure.get("matches", []):
        if not m.get("played"):
            continue
        key = match_key(m)
        if key in result:  # キャッシュ済みはスキップ
            continue
        if count >= max_fixtures:
            break
        fkey = (m.get("date", ""), frozenset((m.get("team1", ""), m.get("team2", ""))))
        api_id = idx.get(fkey)
        if not api_id:
            continue
        count += 1
        try:
            lineups = parse_lineups(fetcher(build_lineups_url(api_id), api_key))
            players = parse_player_stats(fetcher(build_players_url(api_id), api_key))
            team_stats = parse_team_stats(fetcher(build_stats_url(api_id), api_key))
        except FetchError:
            continue
        if lineups or players or team_stats:
            result[key] = {"lineups": lineups, "players": players, "team_stats": team_stats}

    write_json_atomic(f"{data_dir}/lineups.json", {"generated_at": now_iso, "items": result})
    print(f"スタメン {len(result)} 試合分を書き込みました: {data_dir}/lineups.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
