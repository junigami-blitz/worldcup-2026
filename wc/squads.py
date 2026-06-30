"""openfootball worldcup.squads.json（代表メンバー）のパースと年齢計算。

※ 試合ごとのスタメン（先発11名）は openfootball / football-data 無料枠に
存在しないため、ここで扱うのは各チームの代表メンバー（26名）のスカッド。
"""
import json
from datetime import date

from wc.timeutil import parse_iso


def parse_squads(text):
    """squads.json を [{name,fifa_code,group,players:[...]}] に正規化する。"""
    data = json.loads(text)
    out = []
    for t in data:
        players = []
        for p in t.get("players", []):
            club = p.get("club") or {}
            if not isinstance(club, dict):
                club = {"name": str(club)}
            players.append({
                "number": p.get("number"),
                "pos": p.get("pos", ""),
                "name": p.get("name", ""),
                "club": club.get("name", ""),
                "club_country": club.get("country", ""),
                "dob": p.get("date_of_birth", ""),
            })
        out.append({
            "name": t.get("name", ""),
            "fifa_code": t.get("fifa_code", ""),
            "group": t.get("group", ""),
            "players": players,
        })
    return out


def squads_by_team(squads):
    """チーム名 → 選手リスト の辞書。"""
    return {t["name"]: t["players"] for t in squads}


def age_on(dob, ref_iso):
    """生年月日(YYYY-MM-DD)と基準日時(ISO)から満年齢を返す。不正なら None。"""
    if not dob:
        return None
    try:
        y, m, d = (int(x) for x in dob.split("-"))
        born = date(y, m, d)
    except (ValueError, AttributeError):
        return None
    ref_dt = parse_iso(ref_iso)
    ref = ref_dt.date() if ref_dt else date.today()
    return ref.year - born.year - ((ref.month, ref.day) < (born.month, born.day))
