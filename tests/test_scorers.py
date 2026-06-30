from wc.scorers import compute_scorers


def _goal(name, penalty=False, owngoal=False):
    return {"name": name, "minute": "10", "penalty": penalty, "owngoal": owngoal}


def test_aggregates_and_orders():
    matches = [
        {"played": True, "team1": "Mexico", "team2": "Korea",
         "goals1": [_goal("Quiñones"), _goal("Quiñones")], "goals2": [_goal("Son")]},
        {"played": True, "team1": "Mexico", "team2": "Czech",
         "goals1": [_goal("Quiñones")], "goals2": []},
    ]
    table = compute_scorers(matches)
    assert table[0] == {"name": "Quiñones", "team": "Mexico", "goals": 3, "penalties": 0}
    assert table[1]["name"] == "Son"


def test_penalties_counted_separately():
    matches = [{"played": True, "team1": "A", "team2": "B",
                "goals1": [_goal("P", penalty=True), _goal("P")], "goals2": []}]
    row = compute_scorers(matches)[0]
    assert row["goals"] == 2
    assert row["penalties"] == 1


def test_owngoal_excluded():
    matches = [{"played": True, "team1": "A", "team2": "B",
                "goals1": [_goal("OG", owngoal=True)], "goals2": []}]
    assert compute_scorers(matches) == []


def test_unplayed_ignored():
    matches = [{"played": False, "team1": "A", "team2": "B",
                "goals1": [_goal("X")], "goals2": []}]
    assert compute_scorers(matches) == []
