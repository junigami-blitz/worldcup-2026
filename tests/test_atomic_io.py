import json
from pathlib import Path

from wc.atomic_io import write_json_atomic, read_json_or_none


def test_write_then_read_roundtrip(tmp_path):
    p = tmp_path / "out" / "data.json"
    write_json_atomic(p, {"a": 1, "ja": "日本"})
    assert read_json_or_none(p) == {"a": 1, "ja": "日本"}


def test_read_missing_returns_none(tmp_path):
    assert read_json_or_none(tmp_path / "nope.json") is None


def test_read_corrupt_returns_none(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{ this is not json", encoding="utf-8")
    assert read_json_or_none(p) is None


def test_no_tmp_file_left_behind(tmp_path):
    p = tmp_path / "data.json"
    write_json_atomic(p, {"x": 1})
    assert not (tmp_path / "data.json.tmp").exists()
