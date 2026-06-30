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
