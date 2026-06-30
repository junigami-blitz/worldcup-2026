from datetime import datetime, timezone

from wc.schedule_gate import is_in_match_window


def _m(iso):
    return {"kickoff_utc": iso}


MATCHES = [_m("2026-06-11T19:00:00+00:00"), _m(None)]


def test_inside_window_at_kickoff():
    now = datetime(2026, 6, 11, 19, 0, tzinfo=timezone.utc)
    assert is_in_match_window(MATCHES, now) is True


def test_inside_window_two_hours_in():
    now = datetime(2026, 6, 11, 21, 0, tzinfo=timezone.utc)
    assert is_in_match_window(MATCHES, now) is True


def test_after_window():
    now = datetime(2026, 6, 11, 22, 30, tzinfo=timezone.utc)
    assert is_in_match_window(MATCHES, now) is False


def test_before_kickoff():
    now = datetime(2026, 6, 11, 18, 0, tzinfo=timezone.utc)
    assert is_in_match_window(MATCHES, now) is False


def test_none_kickoff_ignored():
    now = datetime(2026, 6, 11, 19, 0, tzinfo=timezone.utc)
    assert is_in_match_window([_m(None)], now) is False
