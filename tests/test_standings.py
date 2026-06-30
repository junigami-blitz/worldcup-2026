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
    # Korea(GD -2) と Czech(GD -1) は共に勝点1。得失点差タイブレークで Czech が上位
    assert [r["team"] for r in table] == ["Mexico", "Czech", "Korea"]
    assert table[0]["points"] == 6
    assert table[0]["pos"] == 1
    assert table[0]["gd"] == 3
    assert table[1]["team"] == "Czech"
    assert table[1]["points"] == 1   # Czech: 引分1, GD -1
    assert table[2]["team"] == "Korea"
    assert table[2]["points"] == 1   # Korea: 引分1, GD -2


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
