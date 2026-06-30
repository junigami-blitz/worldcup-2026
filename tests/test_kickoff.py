from datetime import datetime, timezone

from wc.kickoff import parse_kickoff_utc


def test_utc_minus_6():
    assert parse_kickoff_utc("2026-06-11", "13:00 UTC-6") == datetime(
        2026, 6, 11, 19, 0, tzinfo=timezone.utc
    )


def test_utc_minus_4():
    assert parse_kickoff_utc("2026-06-18", "12:00 UTC-4") == datetime(
        2026, 6, 18, 16, 0, tzinfo=timezone.utc
    )


def test_rollover_past_midnight():
    # 20:00 UTC-6 -> 02:00 翌日 UTC
    assert parse_kickoff_utc("2026-06-11", "20:00 UTC-6") == datetime(
        2026, 6, 12, 2, 0, tzinfo=timezone.utc
    )


def test_missing_time_returns_none():
    assert parse_kickoff_utc("2026-06-11", "") is None


def test_garbage_returns_none():
    assert parse_kickoff_utc("2026-06-11", "TBD") is None
