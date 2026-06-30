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
