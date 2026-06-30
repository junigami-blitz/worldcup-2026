from wc.matchid import match_key


def test_match_key_is_stable_and_unique():
    m1 = {"date": "2026-06-11", "team1": "Mexico", "team2": "Japan"}
    m2 = {"date": "2026-06-11", "team1": "Japan", "team2": "Mexico"}
    assert match_key(m1) == "2026-06-11|Mexico|Japan"
    assert match_key(m1) != match_key(m2)  # 対戦順が違えば別キー


def test_match_key_handles_missing_fields():
    assert match_key({}) == "||"
