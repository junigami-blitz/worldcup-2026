import json

from wc.news import parse_news_rss, news_url, main

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>ワールドカップ2026 - Google ニュース</title>
<item>
  <title>日本代表、グループ首位通過 &amp; 決勝T進出</title>
  <link>https://news.example.com/a</link>
  <pubDate>Mon, 29 Jun 2026 10:30:00 GMT</pubDate>
  <source url="https://www.nhk.or.jp">NHK</source>
</item>
<item>
  <title>メッシ6得点で得点王争い首位</title>
  <link>https://news.example.com/b</link>
  <pubDate>Sun, 28 Jun 2026 22:00:00 GMT</pubDate>
  <source url="https://www.sponichi.co.jp">スポニチ</source>
</item>
</channel>
</rss>"""


def test_parse_extracts_fields():
    items = parse_news_rss(RSS)
    assert len(items) == 2
    a = items[0]
    assert a["title"] == "日本代表、グループ首位通過 & 決勝T進出"  # 実体参照がデコードされる
    assert a["link"] == "https://news.example.com/a"
    assert a["source"] == "NHK"
    assert a["published"] == "2026-06-29"  # pubDate を YYYY-MM-DD へ整形


def test_parse_respects_limit():
    items = parse_news_rss(RSS, limit=1)
    assert len(items) == 1
    assert items[0]["link"] == "https://news.example.com/a"


def test_parse_broken_xml_returns_empty():
    assert parse_news_rss("<not xml") == []
    assert parse_news_rss("") == []


def test_news_url_encodes_query():
    url = news_url("ワールドカップ 2026")
    assert url.startswith("https://news.google.com/rss/search?q=")
    assert "%E3%83%AF" in url  # 「ワ」のURLエンコード
    assert "hl=ja" in url and "ceid=JP:ja" in url


def test_main_writes_news_json(tmp_path):
    rc = main(out_dir=str(tmp_path), fetcher=lambda url: RSS, now_iso="2026-06-30T00:00:00+00:00")
    assert rc == 0
    data = json.loads((tmp_path / "news.json").read_text(encoding="utf-8"))
    assert data["generated_at"] == "2026-06-30T00:00:00+00:00"
    assert data["items"][0]["source"] == "NHK"


def test_main_preserves_on_fetch_error(tmp_path):
    (tmp_path / "news.json").write_text('{"old": true}', encoding="utf-8")
    from wc.fetch import FetchError

    def broken(url):
        raise FetchError("down")

    rc = main(out_dir=str(tmp_path), fetcher=broken, now_iso="2026-06-30T00:00:00+00:00")
    assert rc == 1
    assert json.loads((tmp_path / "news.json").read_text(encoding="utf-8")) == {"old": True}


def test_parse_extracts_source_url():
    items = parse_news_rss(RSS)
    assert items[0]["source_url"] == "https://www.nhk.or.jp"
