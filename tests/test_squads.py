from wc.squads import parse_squads, squads_by_team, age_on

SQUADS = (
    '[{"name":"Japan","fifa_code":"JPN","group":"A","players":['
    '{"number":1,"pos":"GK","name":"Zion Suzuki","club":{"name":"Parma","country":"ITA"},"date_of_birth":"2002-08-21"},'
    '{"number":10,"pos":"MF","name":"Takefusa Kubo","club":{"name":"Real Sociedad","country":"ESP"},"date_of_birth":"2001-06-04"}'
    ']}]'
)


def test_parse_squads_fields():
    s = parse_squads(SQUADS)
    assert len(s) == 1
    t = s[0]
    assert t["name"] == "Japan"
    p = t["players"][0]
    assert p["number"] == 1
    assert p["pos"] == "GK"
    assert p["name"] == "Zion Suzuki"
    assert p["club"] == "Parma"
    assert p["dob"] == "2002-08-21"


def test_squads_by_team_index():
    by = squads_by_team(parse_squads(SQUADS))
    assert "Japan" in by
    assert len(by["Japan"]) == 2


def test_age_on():
    # 2001-06-04 生まれ、2026-07-01 時点で25歳
    assert age_on("2001-06-04", "2026-07-01T00:00:00+00:00") == 25
    # 誕生日前（2002-08-21、2026-07-01時点で23歳）
    assert age_on("2002-08-21", "2026-07-01T00:00:00+00:00") == 23
    assert age_on("", "2026-07-01T00:00:00+00:00") is None
    assert age_on("bad", "2026-07-01T00:00:00+00:00") is None
