"""Google News RSS（日本語）から大会ニュースを取得し data/news.json を生成する。"""
import sys
from email.utils import parsedate_to_datetime
from urllib.parse import quote
from xml.etree import ElementTree as ET

from wc.fetch import fetch_text, FetchError
from wc.atomic_io import write_json_atomic

DEFAULT_QUERY = "ワールドカップ2026"


def news_url(query):
    """Google News RSS 検索URL（日本語ロケール）を返す。"""
    q = quote(query)
    return f"https://news.google.com/rss/search?q={q}&hl=ja&gl=JP&ceid=JP:ja"


def _fmt_date(pubdate):
    """RFC822形式の pubDate を YYYY-MM-DD に整形。失敗時は元文字列。"""
    if not pubdate:
        return ""
    try:
        return parsedate_to_datetime(pubdate).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return pubdate


def parse_news_rss(xml_text, limit=20):
    """RSS本文から記事リストを返す（純粋）。壊れたXMLは空リスト。"""
    if not xml_text:
        return []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    items = []
    for item in root.findall("./channel/item")[:limit]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        src_el = item.find("source")
        source = (src_el.text or "").strip() if src_el is not None else ""
        items.append({
            "title": title,
            "link": link,
            "source": source,
            "published": _fmt_date(pub),
        })
    return items


def main(out_dir="data", query=DEFAULT_QUERY, fetcher=fetch_text, now_iso=None):
    """RSS取得→パース→data/news.json 書き込み。失敗時は既存保持で 1。"""
    if now_iso is None:
        from datetime import datetime, timezone
        now_iso = datetime.now(timezone.utc).isoformat()
    try:
        xml_text = fetcher(news_url(query))
    except FetchError as e:
        print(f"ニュース取得失敗のため既存データを保持します: {e}", file=sys.stderr)
        return 1
    items = parse_news_rss(xml_text)
    write_json_atomic(f"{out_dir}/news.json", {"generated_at": now_iso, "items": items})
    print(f"ニュース {len(items)} 件を書き込みました: {out_dir}/news.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
