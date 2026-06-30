import json

from wc.apifootball import (
    parse_fixtures, parse_lineups, parse_player_stats, parse_team_stats,
    build_fixtures_url, build_lineups_url, normalize_af_name, fetch_af,
)

FIXTURES_JSON = json.dumps({
    "response": [
        {"fixture": {"id": 1200, "date": "2026-06-11T19:00:00+00:00"},
         "teams": {"home": {"name": "Mexico"}, "away": {"name": "Korea Republic"}}},
        {"fixture": {"id": 1201, "date": "2026-06-12T16:00:00+00:00"},
         "teams": {"home": {"name": "USA"}, "away": {"name": "England"}}},
    ]
})

LINEUPS_JSON = json.dumps({
    "response": [
        {"team": {"name": "Mexico"}, "formation": "4-3-3",
         "coach": {"name": "Javier Aguirre"},
         "startXI": [
             {"player": {"id": 1, "name": "Ochoa", "number": 13, "pos": "G", "grid": "1:1"}},
             {"player": {"id": 2, "name": "Álvarez", "number": 4, "pos": "M", "grid": "3:2"}},
         ],
         "substitutes": [
             {"player": {"id": 9, "name": "Vega", "number": 10, "pos": "F", "grid": None}},
         ]},
        {"team": {"name": "Korea Republic"}, "formation": "4-2-3-1",
         "coach": {"name": "Hong Myung-bo"},
         "startXI": [{"player": {"id": 50, "name": "Kim", "number": 1, "pos": "G", "grid": "1:1"}}],
         "substitutes": []},
    ]
})

PLAYERS_JSON = json.dumps({
    "response": [
        {"team": {"name": "Mexico"}, "players": [
            {"player": {"id": 2, "name": "Edson Álvarez"}, "statistics": [
                {"games": {"minutes": 90, "rating": "7.5", "position": "M", "captain": True, "substitute": False},
                 "goals": {"total": 1, "assists": None},
                 "shots": {"total": 3, "on": 2},
                 "passes": {"total": 56, "key": 2, "accuracy": "88"},
                 "cards": {"yellow": 1, "red": 0}}
            ]}
        ]}
    ]
})

STATS_JSON = json.dumps({
    "response": [
        {"team": {"name": "Mexico"}, "statistics": [
            {"type": "Ball Possession", "value": "55%"},
            {"type": "Total Shots", "value": 12},
            {"type": "Shots on Goal", "value": 5},
        ]},
        {"team": {"name": "Korea Republic"}, "statistics": [
            {"type": "Ball Possession", "value": "45%"},
            {"type": "Total Shots", "value": 8},
            {"type": "Shots on Goal", "value": None},
        ]},
    ]
})


def test_parse_fixtures_id_map():
    fx = parse_fixtures(FIXTURES_JSON)
    assert fx[0]["api_id"] == 1200
    assert fx[0]["date"] == "2026-06-11"
    assert fx[0]["home"] == "Mexico"
    assert fx[0]["away"] == "Korea Republic"


def test_parse_lineups():
    lus = parse_lineups(LINEUPS_JSON)
    assert len(lus) == 2
    m = lus[0]
    assert m["team"] == "Mexico"
    assert m["formation"] == "4-3-3"
    assert m["coach"] == "Javier Aguirre"
    assert m["startXI"][0]["name"] == "Ochoa"
    assert m["startXI"][0]["number"] == 13
    assert m["startXI"][0]["grid"] == "1:1"
    assert m["substitutes"][0]["name"] == "Vega"


def test_parse_player_stats():
    ps = parse_player_stats(PLAYERS_JSON)
    assert ps[0]["team"] == "Mexico"
    p = ps[0]["players"][0]
    assert p["name"] == "Edson Álvarez"
    assert p["minutes"] == 90
    assert p["rating"] == "7.5"
    assert p["goals"] == 1
    assert p["shots"] == 3
    assert p["passes"] == 56
    assert p["yellow"] == 1


def test_parse_team_stats():
    ts = parse_team_stats(STATS_JSON)
    assert ts[0]["team"] == "Mexico"
    d = {s["type"]: s["value"] for s in ts[0]["stats"]}
    assert d["Ball Possession"] == "55%"
    assert d["Total Shots"] == 12
    # None値は除外/空文字化される
    d2 = {s["type"]: s["value"] for s in ts[1]["stats"]}
    assert d2.get("Shots on Goal", "") in ("", None, 0) or "Shots on Goal" not in d2


def test_normalize_af_name():
    assert normalize_af_name("Korea Republic") == "South Korea"
    assert normalize_af_name("USA") == "USA"
    assert normalize_af_name("Czechia") == "Czech Republic"


def test_build_urls():
    assert "league=1" in build_fixtures_url(2026)
    assert "season=2026" in build_fixtures_url(2026)
    assert "fixtures/lineups?fixture=1200" in build_lineups_url(1200)


def test_parse_broken_returns_empty():
    assert parse_fixtures("<x") == []
    assert parse_lineups("<x") == []
    assert parse_player_stats("<x") == []
    assert parse_team_stats("<x") == []


def test_fetch_af_sends_key_header(monkeypatch):
    captured = {}

    class FakeProc:
        returncode = 0
        stdout = "{}"
        stderr = ""

    def fake_run(cmd, **kw):
        captured["cmd"] = cmd
        return FakeProc()

    monkeypatch.setattr("wc.apifootball.subprocess.run", fake_run)
    fetch_af("https://x", "SECRET")
    assert "x-apisports-key: SECRET" in " ".join(captured["cmd"])
