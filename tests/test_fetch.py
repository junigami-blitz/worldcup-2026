import pytest

from wc.fetch import fetch_text, FetchError


def test_fetch_text_returns_stdout(monkeypatch):
    class FakeProc:
        returncode = 0
        stdout = '{"ok": 1}'
        stderr = ""

    monkeypatch.setattr("wc.fetch.subprocess.run", lambda *a, **k: FakeProc())
    assert fetch_text("https://example.com/x.json") == '{"ok": 1}'


def test_fetch_text_raises_on_nonzero(monkeypatch):
    class FakeProc:
        returncode = 7
        stdout = ""
        stderr = "boom"

    monkeypatch.setattr("wc.fetch.subprocess.run", lambda *a, **k: FakeProc())
    with pytest.raises(FetchError):
        fetch_text("https://example.com/x.json")


def test_fetch_text_raises_on_empty(monkeypatch):
    class FakeProc:
        returncode = 0
        stdout = "   "
        stderr = ""

    monkeypatch.setattr("wc.fetch.subprocess.run", lambda *a, **k: FakeProc())
    with pytest.raises(FetchError):
        fetch_text("https://example.com/x.json")
