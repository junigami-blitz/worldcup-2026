"""試合時間帯（kickoff〜+post_hours）かを判定し、CLIで終了コードを返す。"""
import sys
from datetime import datetime, timedelta, timezone

from wc.atomic_io import read_json_or_none


def is_in_match_window(matches, now_utc, post_hours=3):
    """いずれかの試合の [kickoff, kickoff+post_hours] に now_utc が入れば True。"""
    window = timedelta(hours=post_hours)
    for m in matches:
        iso = m.get("kickoff_utc")
        if not iso:
            continue
        ko = datetime.fromisoformat(iso)
        if ko <= now_utc <= ko + window:
            return True
    return False


def main(argv=None):
    structure = read_json_or_none("data/structure.json")
    if not structure:
        print("SKIP (no structure.json)")
        return 1
    now = datetime.now(timezone.utc)
    if is_in_match_window(structure.get("matches", []), now):
        print("RUN")
        return 0
    print("SKIP")
    return 1


if __name__ == "__main__":
    sys.exit(main())
