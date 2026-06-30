"""openfootballから取得し data/structure.json と data/rankings.json を生成する。

FOOTBALL_DATA_API_KEY があれば football-data の確定スコアで鮮度補完する。
"""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from wc.fetch import fetch_text, FetchError
from wc.openfootball import build_structure
from wc.standings import compute_standings
from wc.scorers import compute_scorers
from wc.atomic_io import write_json_atomic
from wc.footballdata import fetch_fd, build_fd_url, parse_fd_matches, overlay_scores

BASE_URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026"


def build_outputs(wc_text, groups_text, teams_text, now_iso, fd_matches=None):
    """取得テキストから structure dict と rankings dict を生成する（純粋関数）。

    fd_matches（football-dataのパース結果）があれば未消化試合にスコアを鮮度補完する。
    """
    structure = build_structure(wc_text, groups_text, teams_text)
    structure["generated_at"] = now_iso
    if fd_matches:
        overlay_scores(structure, fd_matches)
    matches = structure["matches"]
    rankings = {
        "generated_at": now_iso,
        "standings": compute_standings(matches),
        "scorers": compute_scorers(matches),
    }
    return structure, rankings


def main(fetcher=fetch_text, out_dir="data", now_iso=None, fd_api_key=None, fd_fetcher=None):
    """取得→生成→書き込み。取得失敗時は既存ファイルを保持して 1 を返す。

    fd_api_key（または環境変数 FOOTBALL_DATA_API_KEY）があれば確定スコアで鮮度補完。
    """
    if now_iso is None:
        now_iso = datetime.now(timezone.utc).isoformat()
    try:
        wc_text = fetcher(f"{BASE_URL}/worldcup.json")
        groups_text = fetcher(f"{BASE_URL}/worldcup.groups.json")
        teams_text = fetcher(f"{BASE_URL}/worldcup.teams.json")
    except FetchError as e:
        print(f"取得失敗のため既存データを保持します: {e}", file=sys.stderr)
        return 1

    # football-data による鮮度補完（鍵があれば）
    if fd_api_key is None:
        fd_api_key = os.environ.get("FOOTBALL_DATA_API_KEY", "")
    fd_matches = None
    if fd_api_key:
        try:
            fd_text = fd_fetcher() if fd_fetcher else fetch_fd(build_fd_url(), fd_api_key)
            fd_matches = parse_fd_matches(fd_text)
            print(f"football-data: {len(fd_matches)} 試合を取得（確定分をスコア補完）")
        except FetchError as e:
            print(f"football-data 取得失敗のため openfootball のみ使用: {e}", file=sys.stderr)

    structure, rankings = build_outputs(wc_text, groups_text, teams_text, now_iso, fd_matches)
    out = Path(out_dir)
    write_json_atomic(out / "structure.json", structure)
    write_json_atomic(out / "rankings.json", rankings)
    print(f"書き込み完了: {out}/structure.json, {out}/rankings.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
