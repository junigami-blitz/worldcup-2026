import json

from wc.footballdata import (
    parse_fd_matches, normalize_fd_name, overlay_scores, build_fd_url, fetch_fd,
)

FD_JSON = json.dumps({
    "matches": [
        {"utcDate": "2026-06-11T19:00:00Z", "status": "FINISHED",
         "homeTeam": {"name": "Mexico"}, "awayTeam": {"name": "Korea Republic"},
         "score": {"fullTime": {"home": 3, "away": 1}}},
        {"utcDate": "2026-06-12T16:00:00Z", "status": "SCHEDULED",
         "homeTeam": {"name": "Spain"}, "awayTeam": {"name": "Brazil"},
         "score": {"fullTime": {"home": None, "away": None}}},
    ]
})


def test_parse_fd_matches():
    items = parse_fd_matches(FD_JSON)
    assert len(items) == 2
    a = items[0]
    assert a["date"] == "2026-06-11"
    assert a["home"] == "Mexico"
    assert a["away"] == "Korea Republic"
    assert a["status"] == "FINISHED"
    assert a["score"] == [3, 1]
    assert items[1]["score"] is None  # 未確定はNone


def test_parse_fd_broken_returns_empty():
    assert parse_fd_matches("<not json") == []


def test_normalize_aliases():
    assert normalize_fd_name("Korea Republic") == "South Korea"
    assert normalize_fd_name("United States") == "USA"
    assert normalize_fd_name("Côte d'Ivoire") == "Ivory Coast"
    assert normalize_fd_name("Japan") == "Japan"  # 一致するものはそのまま


def test_overlay_fills_unplayed_match_with_correct_orientation():
    # openfootball側: Korea が team1（fdとは home/away が逆）かつ未消化
    structure = {"matches": [
        {"date": "2026-06-11", "team1": "South Korea", "team2": "Mexico",
         "played": False, "score": None, "goals1": [], "goals2": []},
    ]}
    fd = parse_fd_matches(FD_JSON)
    n = overlay_scores(structure, fd)
    assert n == 1
    m = structure["matches"][0]
    assert m["played"] is True
    # fdは Mexico 3 - 1 Korea。team1=Korea なので [1,3] に並べ替えられる
    assert m["score"]["ft"] == [1, 3]


def test_overlay_skips_already_played():
    structure = {"matches": [
        {"date": "2026-06-11", "team1": "Mexico", "team2": "South Korea",
         "played": True, "score": {"ft": [2, 0]},
         "goals1": [{"name": "X", "minute": "5", "penalty": False, "owngoal": False}], "goals2": []},
    ]}
    fd = parse_fd_matches(FD_JSON)
    n = overlay_scores(structure, fd)
    assert n == 0  # 既に消化済み（得点者あり）は上書きしない
    assert structure["matches"][0]["score"]["ft"] == [2, 0]


def test_overlay_skips_non_finished_and_no_match():
    structure = {"matches": [
        {"date": "2026-06-12", "team1": "Spain", "team2": "Brazil",
         "played": False, "score": None, "goals1": [], "goals2": []},  # fdではSCHEDULED
        {"date": "2026-06-11", "team1": "Foo", "team2": "Bar",
         "played": False, "score": None, "goals1": [], "goals2": []},  # 該当なし
    ]}
    fd = parse_fd_matches(FD_JSON)
    assert overlay_scores(structure, fd) == 0


def test_build_fd_url_targets_wc():
    assert "competitions/WC/matches" in build_fd_url()


def test_fetch_fd_sends_auth_header(monkeypatch):
    captured = {}

    class FakeProc:
        returncode = 0
        stdout = "{}"
        stderr = ""

    def fake_run(cmd, **kw):
        captured["cmd"] = cmd
        return FakeProc()

    monkeypatch.setattr("wc.footballdata.subprocess.run", fake_run)
    fetch_fd("https://x", "SECRET")
    joined = " ".join(captured["cmd"])
    assert "X-Auth-Token: SECRET" in joined
