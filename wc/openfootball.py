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
    for idx, m in enumerate(data.get("matches", [])):
        round_name = m.get("round", "")
        stage = "knockout" if round_name in _KNOCKOUT_ROUNDS else "group"
        score = m.get("score")
        played = bool(score and score.get("ft"))
        ko = parse_kickoff_utc(m.get("date", ""), m.get("time", ""))
        out.append({
            # num はノックアウトのみ原データに存在。グループ等は出現順で採番(1始まり)。
            # グループはファイル先頭に並ぶため 1〜72 ＝ FIFA公式試合番号と一致する。
            "num": m.get("num") if m.get("num") is not None else idx + 1,
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
