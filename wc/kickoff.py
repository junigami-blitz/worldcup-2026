"""openfootball の "13:00 UTC-6" 形式の時刻を UTC aware datetime に変換する。"""
import re
from datetime import datetime, timedelta, timezone

_PATTERN = re.compile(r"^\s*(\d{1,2}):(\d{2})\s+UTC([+-]\d{1,2})\s*$")


def parse_kickoff_utc(date_str, time_str):
    """date_str(YYYY-MM-DD) と time_str("HH:MM UTC±N") から UTC datetime を返す。

    解析できない場合は None。
    """
    if not time_str:
        return None
    m = _PATTERN.match(time_str)
    if not m:
        return None
    hour, minute, offset = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        y, mo, d = (int(x) for x in date_str.split("-"))
        local_naive = datetime(y, mo, d, hour, minute)
    except (ValueError, AttributeError):
        return None
    # UTC = ローカル - オフセット時間（UTC-6 なら +6h して UTC へ）
    utc = local_naive - timedelta(hours=offset)
    return utc.replace(tzinfo=timezone.utc)
