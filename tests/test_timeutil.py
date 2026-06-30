from datetime import datetime, timezone

from wc.timeutil import to_jst, jst_label, jst_full, parse_iso


def test_to_jst_adds_9_hours():
    # 19:00 UTC -> 翌日 04:00 JST
    dt = to_jst("2026-06-11T19:00:00+00:00")
    assert (dt.year, dt.month, dt.day, dt.hour, dt.minute) == (2026, 6, 12, 4, 0)


def test_to_jst_none_on_garbage():
    assert to_jst("") is None
    assert to_jst(None) is None
    assert to_jst("not-a-date") is None


def test_jst_label_format():
    # 2026-06-12 は金曜日
    label = jst_label("2026-06-11T19:00:00+00:00")
    assert "6/12" in label
    assert "04:00" in label
    assert "(金)" in label


def test_jst_label_empty_on_garbage():
    assert jst_label("") == ""
    assert jst_label(None) == ""


def test_jst_full_format():
    assert jst_full("2026-06-11T19:00:00+00:00") == "2026/06/12 04:00 JST"


def test_jst_full_empty_on_garbage():
    assert jst_full("") == ""


def test_parse_iso_returns_aware_datetime():
    dt = parse_iso("2026-06-30T00:00:00+00:00")
    assert dt == datetime(2026, 6, 30, tzinfo=timezone.utc)
    assert parse_iso("bad") is None
