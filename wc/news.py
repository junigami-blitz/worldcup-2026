"""大会ニュースを取得し data/news.json を生成する。

- GNEWS_API_KEY があれば GNews API（gnews.io）を主データ源にする。
  記事に実URLとアイキャッチ画像(image)が含まれるため、サムネに本物の画像を使える。
- 鍵が無い/GNewsが失敗した場合は Google News RSS（日本語）にフォールバックする。
  RSSは記事画像を提供せず（linkもGoogle経由の中継URL）、サムネは配信元faviconになる。
- 鍵がある場合も RSS を併用してマージする。GNews無料枠は1リクエスト最大10件と
  少ないため、RSSの広いカバレッジ（〜100件）で関連ニュース照合を維持しつつ、
  GNewsの画像付き記事を先頭に上書きする。
"""
import json
import os
import sys
from email.utils import parsedate_to_datetime
from urllib.parse import quote
from xml.etree import ElementTree as ET

from wc.fetch import fetch_text, FetchError
from wc.atomic_io import write_json_atomic

DEFAULT_QUERY = "ワールドカップ2026"
GNEWS_HOST = "https://gnews.io/api/v4"


# ---- Google News RSS（フォールバック） ----

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


def parse_news_rss(xml_text, limit=100):
    """RSS本文から記事リストを返す（純粋）。壊れたXMLは空リスト。

    RSSは記事画像を提供しないため image は常に空文字（スキーマ統一のため付与）。
    """
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
        source_url = (src_el.get("url") or "").strip() if src_el is not None else ""
        items.append({
            "title": title,
            "link": link,
            "source": source,
            "source_url": source_url,
            "published": _fmt_date(pub),
            "image": "",
        })
    return items


# ---- GNews API（鍵があれば主データ源） ----

def build_gnews_url(api_key, query=DEFAULT_QUERY, lang="ja", country="jp",
                    max_articles=10):
    """GNews search API のURL。無料枠は max=10・100req/日。"""
    q = quote(query)
    return (f"{GNEWS_HOST}/search?q={q}&lang={lang}&country={country}"
            f"&max={max_articles}&sortby=publishedAt&apikey={api_key}")


def parse_gnews(json_text, limit=100):
    """GNewsレスポンス→記事リスト。壊れ/エラー(articles無し)は []。"""
    try:
        data = json.loads(json_text)
    except (json.JSONDecodeError, TypeError):
        return []
    arts = data.get("articles") if isinstance(data, dict) else None
    if not arts:
        return []
    items = []
    for a in arts[:limit]:
        src = a.get("source") or {}
        items.append({
            "title": (a.get("title") or "").strip(),
            "link": (a.get("url") or "").strip(),
            "source": (src.get("name") or "").strip(),
            "source_url": (src.get("url") or "").strip(),
            "published": (a.get("publishedAt") or "")[:10],
            "image": (a.get("image") or "").strip(),
        })
    return items


def _title_key(title):
    """重複判定用にタイトルを正規化（英字小文字化・空白/記号除去）。"""
    return "".join(ch.lower() for ch in (title or "") if ch.isalnum())


def merge_news(primary, secondary):
    """primary(GNews:画像あり)を優先し、secondary(RSS)は未登場タイトルのみ追加。

    GNewsの画像付き・実URL記事を先頭に、RSSの広いカバレッジを後段に残す。
    重複判定は正規化タイトルの包含（GNewsとRSSで語尾が異なる同一記事も除去）。
    """
    seen = []
    out = []

    def is_dup(k):
        if not k:
            return True
        for s in seen:
            if k == s:
                return True
            # 一方が他方を含む＝実質同一記事（8字以上で誤爆を防ぐ）
            if len(k) >= 8 and len(s) >= 8 and (k in s or s in k):
                return True
        return False

    for it in list(primary) + list(secondary):
        k = _title_key(it.get("title", ""))
        if is_dup(k):
            continue
        seen.append(k)
        out.append(it)
    return out


def main(out_dir="data", query=DEFAULT_QUERY, fetcher=fetch_text, now_iso=None,
         api_key=None):
    """ニュース取得→data/news.json 書き込み。取得失敗時は既存保持で 1。

    鍵があれば GNews(画像) + RSS(カバレッジ) をマージ。無ければ RSS のみ。
    """
    if now_iso is None:
        from datetime import datetime, timezone
        now_iso = datetime.now(timezone.utc).isoformat()
    if api_key is None:
        api_key = os.environ.get("GNEWS_API_KEY", "")

    # RSS（カバレッジ用・フォールバック用）
    rss_items = []
    try:
        rss_items = parse_news_rss(fetcher(news_url(query)))
    except FetchError as e:
        print(f"RSS取得失敗: {e}", file=sys.stderr)

    items = rss_items
    if api_key:
        try:
            gnews_items = parse_gnews(fetcher(build_gnews_url(api_key, query)))
        except FetchError as e:
            print(f"GNews取得失敗（RSSのみで継続）: {e}", file=sys.stderr)
            gnews_items = []
        if gnews_items:
            items = merge_news(gnews_items, rss_items)

    if not items:
        print("ニュースが0件のため既存データを保持します。", file=sys.stderr)
        return 1

    write_json_atomic(f"{out_dir}/news.json", {"generated_at": now_iso, "items": items})
    n_img = sum(1 for it in items if it.get("image"))
    print(f"ニュース {len(items)} 件（画像付き {n_img} 件）を書き込みました: {out_dir}/news.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
