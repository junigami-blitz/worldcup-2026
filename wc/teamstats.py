"""全消化試合（グループ＋ノックアウト）からチーム別の得点・失点を集計する。"""


def compute_team_stats(matches):
    """チーム別 {team, played, gf, ga, gd} を総得点降順で返す。

    対象は played==True の全試合（グループ・ノックアウト両方）。
    並び: 総得点降順 → 得失点差降順 → チーム名昇順。
    """
    tally = {}
    for m in matches:
        if not m.get("played") or not m.get("score"):
            continue
        a, b = m["score"]["ft"][0], m["score"]["ft"][1]
        for team, gf, ga in ((m["team1"], a, b), (m["team2"], b, a)):
            r = tally.setdefault(team, {"team": team, "played": 0, "gf": 0, "ga": 0})
            r["played"] += 1
            r["gf"] += gf
            r["ga"] += ga
    rows = list(tally.values())
    for r in rows:
        r["gd"] = r["gf"] - r["ga"]
    rows.sort(key=lambda r: (-r["gf"], -r["gd"], r["team"]))
    return rows
