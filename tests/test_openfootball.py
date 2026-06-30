from wc.openfootball import (
    parse_groups, parse_teams, parse_matches, build_structure,
)

GROUPS = '{"name":"WC","groups":[{"name":"Group A","teams":["Mexico","South Africa"]}]}'
TEAMS = (
    '[{"name":"Mexico","continent":"North America","flag_icon":"\\ud83c\\uddf2\\ud83c\\uddfd",'
    '"fifa_code":"MEX","group":"A","confed":"CONCACAF"}]'
)
MATCHES = (
    '{"name":"WC","matches":['
    '{"round":"Matchday 1","date":"2026-06-11","time":"13:00 UTC-6",'
    '"team1":"Mexico","team2":"South Africa","score":{"ft":[2,0],"ht":[1,0]},'
    '"goals1":[{"name":"Quiñones","minute":"9"},{"name":"Jiménez","minute":"67","penalty":true}],'
    '"goals2":[],"group":"Group A","ground":"Mexico City"},'
    '{"round":"Final","date":"2026-07-19","time":"15:00 UTC-4",'
    '"team1":"Brazil","team2":"Germany","goals1":[],"goals2":[],"ground":"New York"}'
    ']}'
)


def test_parse_groups():
    assert parse_groups(GROUPS) == [
        {"name": "Group A", "teams": ["Mexico", "South Africa"]}
    ]


def test_parse_teams_keeps_key_fields():
    t = parse_teams(TEAMS)[0]
    assert t["name"] == "Mexico"
    assert t["fifa_code"] == "MEX"
    assert t["group"] == "A"
    assert t["confed"] == "CONCACAF"


def test_parse_matches_group_played():
    m = parse_matches(MATCHES)[0]
    assert m["stage"] == "group"
    assert m["group"] == "Group A"
    assert m["played"] is True
    assert m["score"]["ft"] == [2, 0]
    assert m["kickoff_utc"] == "2026-06-11T19:00:00+00:00"
    assert m["goals1"][1]["penalty"] is True
    assert m["goals1"][0]["penalty"] is False


def test_parse_matches_knockout_unplayed():
    m = parse_matches(MATCHES)[1]
    assert m["stage"] == "knockout"
    assert m["group"] is None
    assert m["played"] is False
    assert m["score"] is None


def test_build_structure_combines_all():
    s = build_structure(MATCHES, GROUPS, TEAMS)
    assert s["name"]
    assert len(s["groups"]) == 1
    assert len(s["teams"]) == 1
    assert len(s["matches"]) == 2
    assert "generated_at" not in s  # 呼び出し側が注入する
