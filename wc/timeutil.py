"""UTC ISO文字列を日本時間(JST)へ変換し、表示用に整形する。"""
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
_WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]


def parse_iso(iso):
    """ISO8601文字列を aware datetime に。失敗時 None。"""
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso)
    except (ValueError, TypeError):
        return None


def to_jst(iso):
    """UTC ISO文字列を JST の datetime に変換。失敗時 None。"""
    dt = parse_iso(iso)
    if dt is None:
        return None
    return dt.astimezone(JST)


def jst_label(iso):
    """キックオフ表示用 "M/D (曜) HH:MM"（JST）。失敗時 空文字。"""
    dt = to_jst(iso)
    if dt is None:
        return ""
    wd = _WEEKDAY_JP[dt.weekday()]
    return f"{dt.month}/{dt.day} ({wd}) {dt.hour:02d}:{dt.minute:02d}"


def jst_full(iso):
    """フッター等の絶対時刻 "YYYY/MM/DD HH:MM JST"。失敗時 空文字。"""
    dt = to_jst(iso)
    if dt is None:
        return ""
    return dt.strftime("%Y/%m/%d %H:%M JST")
