import json
from pathlib import Path

import pytest

from wc.update_data import build_outputs, main
from wc.fetch import FetchError

GROUPS = '{"name":"WC","groups":[{"name":"Group A","teams":["Mexico","Korea"]}]}'
TEAMS = '[{"name":"Mexico","fifa_code":"MEX","group":"A","confed":"CONCACAF","flag_icon":"x","continent":"NA"}]'
MATCHES = (
    '{"name":"WC","matches":['
    '{"round":"Matchday 1","date":"2026-06-11","time":"13:00 UTC-6",'
    '"team1":"Mexico","team2":"Korea","score":{"ft":[2,0],"ht":[1,0]},'
    '"goals1":[{"name":"Quiñones","minute":"9"}],"goals2":[],"group":"Group A","ground":"X"}'
    ']}'
)


def test_build_outputs_shapes():
    structure, rankings = build_outputs(MATCHES, GROUPS, TEAMS, "2026-06-30T00:00:00+00:00")
    assert structure["generated_at"] == "2026-06-30T00:00:00+00:00"
    assert len(structure["matches"]) == 1
    assert rankings["standings"]["Group A"][0]["team"] == "Mexico"
    assert rankings["scorers"][0]["name"] == "Quiñones"


def _fake_fetcher(url):
    if url.endswith("worldcup.json"):
        return MATCHES
    if url.endswith("worldcup.groups.json"):
        return GROUPS
    if url.endswith("worldcup.teams.json"):
        return TEAMS
    raise AssertionError(url)


def test_main_writes_files(tmp_path):
    rc = main(fetcher=_fake_fetcher, out_dir=str(tmp_path), now_iso="2026-06-30T00:00:00+00:00")
    assert rc == 0
    structure = json.loads((tmp_path / "structure.json").read_text(encoding="utf-8"))
    rankings = json.loads((tmp_path / "rankings.json").read_text(encoding="utf-8"))
    assert structure["matches"][0]["team1"] == "Mexico"
    assert rankings["scorers"][0]["goals"] == 1


def test_build_outputs_overlays_fd_scores():
    # openfootball では未消化の Mexico-Korea に football-data の結果を反映
    fd = [{"date": "2026-06-11", "home": "Mexico", "away": "Korea",
           "status": "FINISHED", "score": [4, 0]}]
    unplayed = (
        '{"name":"WC","matches":['
        '{"round":"Matchday 1","date":"2026-06-11","time":"13:00 UTC-6",'
        '"team1":"Mexico","team2":"Korea","goals1":[],"goals2":[],"group":"Group A","ground":"X"}'
        ']}'
    )
    structure, rankings = build_outputs(unplayed, GROUPS, TEAMS, "2026-06-30T00:00:00+00:00", fd_matches=fd)
    m = structure["matches"][0]
    assert m["played"] is True
    assert m["score"]["ft"] == [4, 0]
    # 反映された結果が順位表にも効く
    assert rankings["standings"]["Group A"][0]["team"] == "Mexico"


def test_main_overlays_with_fd_key(tmp_path):
    import json as _json
    unplayed_matches = (
        '{"name":"WC","matches":['
        '{"round":"Matchday 1","date":"2026-06-11","time":"13:00 UTC-6",'
        '"team1":"Mexico","team2":"Korea","goals1":[],"goals2":[],"group":"Group A","ground":"X"}'
        ']}'
    )

    def fake_fetcher(url):
        if url.endswith("worldcup.json"):
            return unplayed_matches
        if url.endswith("worldcup.groups.json"):
            return GROUPS
        if url.endswith("worldcup.teams.json"):
            return TEAMS
        raise AssertionError(url)

    fd_json = _json.dumps({"matches": [
        {"utcDate": "2026-06-11T19:00:00Z", "status": "FINISHED",
         "homeTeam": {"name": "Mexico"}, "awayTeam": {"name": "Korea"},
         "score": {"fullTime": {"home": 2, "away": 1}}},
    ]})

    rc = main(fetcher=fake_fetcher, out_dir=str(tmp_path), now_iso="2026-06-30T00:00:00+00:00",
              fd_api_key="KEY", fd_fetcher=lambda: fd_json)
    assert rc == 0
    structure = _json.loads((tmp_path / "structure.json").read_text(encoding="utf-8"))
    assert structure["matches"][0]["played"] is True
    assert structure["matches"][0]["score"]["ft"] == [2, 1]


def test_main_preserves_files_on_fetch_error(tmp_path):
    # 既存の正常ファイルを置いておく
    (tmp_path / "structure.json").write_text('{"old": true}', encoding="utf-8")

    def broken(url):
        raise FetchError("network down")

    rc = main(fetcher=broken, out_dir=str(tmp_path), now_iso="2026-06-30T00:00:00+00:00")
    assert rc == 1
    # 既存ファイルは壊されない
    assert json.loads((tmp_path / "structure.json").read_text(encoding="utf-8")) == {"old": True}
