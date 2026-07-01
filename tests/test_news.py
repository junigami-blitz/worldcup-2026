import json

from wc.news import (
    parse_news_rss, news_url, main,
    parse_gnews, build_gnews_url, merge_news,
)

GNEWS = json.dumps({
    "totalArticles": 2,
    "articles": [
        {
            "title": "日本代表、グループ首位通過",
            "url": "https://real.example.com/jp-top",
            "image": "https://img.example.com/jp.jpg",
            "publishedAt": "2026-06-29T10:30:00Z",
            "source": {"name": "NHK", "url": "https://www.nhk.or.jp"},
        },
        {
            "title": "メッシ6得点で得点王争い首位",
            "url": "https://real.example.com/messi",
            "image": "",  # 画像なし記事もある
            "publishedAt": "2026-06-28T22:00:00Z",
            "source": {"name": "スポニチ", "url": "https://www.sponichi.co.jp"},
        },
    ],
})

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


# ---- GNews API ----

def test_build_gnews_url_has_key_and_lang():
    url = build_gnews_url("KEY123", query="ワールドカップ2026", max_articles=10)
    assert url.startswith("https://gnews.io/api/v4/search?")
    assert "apikey=KEY123" in url
    assert "lang=ja" in url and "country=jp" in url
    assert "max=10" in url
    assert "%E3%83%AF" in url  # 「ワ」がURLエンコードされる


def test_parse_gnews_maps_fields_and_image():
    items = parse_gnews(GNEWS)
    assert len(items) == 2
    a = items[0]
    assert a["title"] == "日本代表、グループ首位通過"
    assert a["link"] == "https://real.example.com/jp-top"      # 実URL（Google経由でない）
    assert a["source"] == "NHK"
    assert a["source_url"] == "https://www.nhk.or.jp"
    assert a["published"] == "2026-06-29"                       # ISO→YYYY-MM-DD
    assert a["image"] == "https://img.example.com/jp.jpg"       # アイキャッチ
    assert items[1]["image"] == ""                             # 画像なしは空文字


def test_parse_gnews_broken_or_error_returns_empty():
    assert parse_gnews("<not json") == []
    assert parse_gnews("") == []
    assert parse_gnews('{"errors": ["Invalid api key"]}') == []  # articles無し


def test_rss_items_have_image_key():
    items = parse_news_rss(RSS)
    assert all("image" in it for it in items)  # スキーマ統一（RSSは空）
    assert items[0]["image"] == ""


# ---- merge_news（GNews画像 + RSSカバレッジ） ----

def test_merge_prefers_gnews_and_dedups_by_title():
    gnews = parse_gnews(GNEWS)          # 2件（画像あり/なし）
    rss = parse_news_rss(RSS)           # 同一タイトル2件（favicon・画像なし）
    merged = merge_news(gnews, rss)
    # 同一タイトルはGNews側（実URL・画像）が採用され重複しない
    assert len(merged) == 2
    assert merged[0]["link"] == "https://real.example.com/jp-top"
    assert merged[0]["image"] == "https://img.example.com/jp.jpg"


def test_merge_appends_rss_only_titles_for_coverage():
    gnews = parse_gnews(GNEWS)
    rss = parse_news_rss(RSS) + [{
        "title": "別大会の速報", "link": "https://news.google.com/rss/x",
        "source": "他社", "source_url": "https://x.example", "published": "2026-06-27",
        "image": "",
    }]
    merged = merge_news(gnews, rss)
    titles = [m["title"] for m in merged]
    assert "別大会の速報" in titles          # RSS固有はカバレッジとして残る
    assert titles.index("日本代表、グループ首位通過") == 0  # GNewsが先頭


# ---- main の鍵ゲート ----

def test_main_uses_gnews_when_key_present(tmp_path):
    def fetcher(url):
        return GNEWS if url.startswith("https://gnews.io") else RSS
    rc = main(out_dir=str(tmp_path), fetcher=fetcher,
              now_iso="2026-06-30T00:00:00+00:00", api_key="KEY")
    assert rc == 0
    data = json.loads((tmp_path / "news.json").read_text(encoding="utf-8"))
    top = data["items"][0]
    assert top["image"] == "https://img.example.com/jp.jpg"   # 画像が入る
    assert top["link"].startswith("https://real.example.com")  # 実URL


def test_main_falls_back_to_rss_without_key(tmp_path):
    rc = main(out_dir=str(tmp_path), fetcher=lambda url: RSS,
              now_iso="2026-06-30T00:00:00+00:00", api_key="")
    assert rc == 0
    data = json.loads((tmp_path / "news.json").read_text(encoding="utf-8"))
    assert data["items"][0]["source"] == "NHK"
    assert data["items"][0]["image"] == ""   # RSSは画像なし
