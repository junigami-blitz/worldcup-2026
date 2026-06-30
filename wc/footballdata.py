"""football-data.org（無料枠）から確定スコアを取得し openfootball に鮮度補完する。

無料枠は得点者・詳細スタッツ非対応のため、用途は「openfootballで未消化の試合に
確定スコアだけを上書き」する鮮度補完に限定する。得点者は openfootball が後追いで埋める。
チーム名表記がソース間で異なるためエイリアスで正規化し、一致しない試合は上書きしない。
"""
import subprocess

from wc.fetch import FetchError
from wc.matchid import match_key  # noqa: F401  (将来の拡張用)

FD_URL = "https://api.football-data.org/v4/competitions/WC/matches"

# football-data の表記 → openfootball の表記（既知の差分のみ。未知はそのまま）
# ※ live API 未検証のためベストエフォート。一致しなければ上書きしないので安全。
FD_TEAM_ALIASES = {
    "Korea Republic": "South Korea",
    "United States": "USA",
    "Côte d'Ivoire": "Ivory Coast",
    "Cote d'Ivoire": "Ivory Coast",
    "IR Iran": "Iran",
    "Türkiye": "Turkey",
    "Turkiye": "Turkey",
    "Czechia": "Czech Republic",
    "Cabo Verde": "Cape Verde",
    "Bosnia and Herzegovina": "Bosnia & Herzegovina",
    "DR Congo": "DR Congo",
}


def normalize_fd_name(name):
    """football-data のチーム名を openfootball の表記へ正規化する。"""
    return FD_TEAM_ALIASES.get(name, name)


def build_fd_url():
    return FD_URL


def fetch_fd(url, api_key, timeout=30):
    """X-Auth-Token ヘッダ付きで football-data API を取得する。失敗時 FetchError。"""
    try:
        proc = subprocess.run(
            ["curl", "-sL", "--fail", "--max-time", str(timeout),
             "-H", f"X-Auth-Token: {api_key}", url],
            capture_output=True, text=True, timeout=timeout + 5,
        )
    except subprocess.TimeoutExpired as e:
        raise FetchError(f"timeout: {url}") from e
    if proc.returncode != 0:
        raise FetchError(f"curl exit {proc.returncode}: {url} {proc.stderr.strip()}")
    if not proc.stdout or not proc.stdout.strip():
        raise FetchError(f"empty response: {url}")
    return proc.stdout


def parse_fd_matches(json_text):
    """football-data /matches レスポンスを [{date,home,away,status,score}] に変換。"""
    import json
    try:
        data = json.loads(json_text)
    except (json.JSONDecodeError, TypeError):
        return []
    out = []
    for m in data.get("matches", []):
        ft = (m.get("score") or {}).get("fullTime") or {}
        h, a = ft.get("home"), ft.get("away")
        score = [h, a] if (h is not None and a is not None) else None
        out.append({
            "date": (m.get("utcDate") or "")[:10],
            "home": (m.get("homeTeam") or {}).get("name", ""),
            "away": (m.get("awayTeam") or {}).get("name", ""),
            "status": m.get("status", ""),
            "score": score,
        })
    return out


def overlay_scores(structure, fd_matches):
    """football-dataのFINISHEDスコアを、openfootballで未消化の一致試合に上書きする。

    一致条件: 同日 かつ {team1,team2} == {home正規化, away正規化}。
    スコアは team1/team2 の並びに合わせて向きを調整する。
    既に played==True の試合（得点者を持つ）は上書きしない。
    戻り値: 上書きした試合数。
    """
    # (date, frozenset(teams)) -> fd entry
    index = {}
    for fm in fd_matches:
        if fm.get("status") != "FINISHED" or not fm.get("score"):
            continue
        home = normalize_fd_name(fm["home"])
        away = normalize_fd_name(fm["away"])
        index[(fm["date"], frozenset((home, away)))] = (home, away, fm["score"])

    count = 0
    for m in structure.get("matches", []):
        if m.get("played"):
            continue
        key = (m.get("date", ""), frozenset((m.get("team1", ""), m.get("team2", ""))))
        hit = index.get(key)
        if not hit:
            continue
        home, away, score = hit
        if m["team1"] == home and m["team2"] == away:
            ft = [score[0], score[1]]
        elif m["team1"] == away and m["team2"] == home:
            ft = [score[1], score[0]]
        else:
            continue  # 同名2チーム等の異常はスキップ
        m["played"] = True
        m["score"] = {"ft": ft}
        count += 1
    return count
