from wc.teamstats import compute_team_stats


def _m(t1, t2, ft, played=True):
    return {"team1": t1, "team2": t2, "played": played,
            "score": {"ft": ft} if played else None}


def test_aggregates_goals_for_and_against():
    matches = [
        _m("Japan", "Spain", [3, 1]),
        _m("Japan", "Brazil", [2, 2]),
        _m("Spain", "Brazil", [0, 4]),
    ]
    stats = compute_team_stats(matches)
    by = {r["team"]: r for r in stats}
    assert by["Japan"]["gf"] == 5
    assert by["Japan"]["ga"] == 3
    assert by["Japan"]["gd"] == 2
    assert by["Japan"]["played"] == 2
    assert by["Brazil"]["gf"] == 6  # 2 + 4
    assert by["Brazil"]["ga"] == 2  # 2 + 0


def test_sorted_by_goals_for_desc_then_gd():
    matches = [
        _m("A", "B", [5, 0]),
        _m("C", "D", [5, 4]),
    ]
    stats = compute_team_stats(matches)
    # A も C も gf=5 だが、A は gd=+5、C は gd=+1 → A が上位
    assert stats[0]["team"] == "A"


def test_ignores_unplayed():
    matches = [_m("A", "B", [1, 0]), _m("A", "C", [9, 0], played=False)]
    by = {r["team"]: r for r in compute_team_stats(matches)}
    assert by["A"]["gf"] == 1  # 未消化は無視
    assert "C" not in by
