"""openfootballから取得し data/structure.json と data/rankings.json を生成する。"""
import sys
from datetime import datetime, timezone
from pathlib import Path

from wc.fetch import fetch_text, FetchError
from wc.openfootball import build_structure
from wc.standings import compute_standings
from wc.scorers import compute_scorers
from wc.atomic_io import write_json_atomic

BASE_URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026"


def build_outputs(wc_text, groups_text, teams_text, now_iso):
    """取得テキストから structure dict と rankings dict を生成する（純粋関数）。"""
    structure = build_structure(wc_text, groups_text, teams_text)
    structure["generated_at"] = now_iso
    matches = structure["matches"]
    rankings = {
        "generated_at": now_iso,
        "standings": compute_standings(matches),
        "scorers": compute_scorers(matches),
    }
    return structure, rankings


def main(fetcher=fetch_text, out_dir="data", now_iso=None):
    """取得→生成→書き込み。取得失敗時は既存ファイルを保持して 1 を返す。"""
    if now_iso is None:
        now_iso = datetime.now(timezone.utc).isoformat()
    try:
        wc_text = fetcher(f"{BASE_URL}/worldcup.json")
        groups_text = fetcher(f"{BASE_URL}/worldcup.groups.json")
        teams_text = fetcher(f"{BASE_URL}/worldcup.teams.json")
    except FetchError as e:
        print(f"取得失敗のため既存データを保持します: {e}", file=sys.stderr)
        return 1

    structure, rankings = build_outputs(wc_text, groups_text, teams_text, now_iso)
    out = Path(out_dir)
    write_json_atomic(out / "structure.json", structure)
    write_json_atomic(out / "rankings.json", rankings)
    print(f"書き込み完了: {out}/structure.json, {out}/rankings.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
