"""YouTubeハイライト取得（鍵ゲート方式）。

YOUTUBE_API_KEY が無ければ安全にスキップしパイプラインを止めない。
クォータ節約のため「終了済みかつ未キャッシュの試合」だけを検索する。
誤った非公式動画を避けるため、許可チャンネルを設定できる（未設定なら検索の
最上位＝最も関連度が高い結果を採用）。
"""
import json
import os
import sys
from datetime import datetime, timezone
from urllib.parse import quote

from wc.fetch import fetch_text, FetchError
from wc.atomic_io import read_json_or_none, write_json_atomic
from wc.matchid import match_key

_SEARCH_ENDPOINT = "https://www.googleapis.com/youtube/v3/search"

# 許可チャンネル（優先順位順）。実運用ではFIFA公式・放送局公式のチャンネルIDを設定する。
# 空のままなら検索最上位を採用する（要・実チャンネルIDの確定）。
DEFAULT_ALLOW_CHANNELS = []

# 1回の実行で行う検索の上限（無料枠1万ユニット/日、検索100ユニット/回）
DEFAULT_MAX_SEARCHES = 30


def pick_highlight(items, allow_channels):
    """検索結果から1件を選ぶ（後方互換）。許可外しか無ければ None。"""
    picks = pick_highlights(items, allow_channels, limit=1)
    return picks[0] if picks else None


def pick_highlights(items, allow_channels, limit=4):
    """検索結果から最大 limit 件を選ぶ。

    allow_channels が空なら関連度上位から limit 件。
    指定時は許可チャンネルのみを優先順位順に採用（補充せず・誤動画防止）。
    """
    if not items:
        return []
    if not allow_channels:
        return items[:limit]
    wl = []
    for ch in allow_channels:
        for it in items:
            if it.get("channelId") == ch and it not in wl:
                wl.append(it)
    return wl[:limit]


def search_query(match):
    """試合からYouTube検索クエリを組み立てる。"""
    t1, t2 = match.get("team1", ""), match.get("team2", "")
    return f"{t1} vs {t2} highlights ワールドカップ 2026"


def build_search_url(query, api_key, max_results=5):
    """YouTube Data API v3 の検索URLを組み立てる。"""
    return (
        f"{_SEARCH_ENDPOINT}?part=snippet&type=video&maxResults={max_results}"
        f"&q={quote(query)}&key={api_key}"
    )


def parse_search_results(json_text):
    """YouTube検索APIレスポンスを [{videoId,channelId,channelTitle,title}] に変換。"""
    try:
        data = json.loads(json_text)
    except (json.JSONDecodeError, TypeError):
        return []
    out = []
    for it in data.get("items", []):
        vid = (it.get("id") or {}).get("videoId")
        sn = it.get("snippet") or {}
        if not vid:
            continue
        out.append({
            "videoId": vid,
            "channelId": sn.get("channelId", ""),
            "channelTitle": sn.get("channelTitle", ""),
            "title": sn.get("title", ""),
        })
    return out


def fetch_highlights(matches, api_key, existing=None, fetcher=fetch_text,
                     allow_channels=None, max_searches=DEFAULT_MAX_SEARCHES, per_match=4):
    """終了済みかつ未キャッシュの試合だけ検索し、{key:{videos:[...]}} を返す。

    各試合 per_match 本まで保持。既存キャッシュ（videos済）は保持。
    max_searches で1回の検索回数を制限。
    """
    result = dict(existing or {})
    allow = DEFAULT_ALLOW_CHANNELS if allow_channels is None else allow_channels
    count = 0
    for m in matches:
        if not m.get("played"):
            continue
        key = match_key(m)
        if result.get(key, {}).get("videos"):  # 新フォーマットでキャッシュ済みならスキップ
            continue
        if count >= max_searches:
            break
        count += 1
        try:
            results = parse_search_results(fetcher(build_search_url(search_query(m), api_key)))
        except FetchError:
            continue
        picks = pick_highlights(results, allow, limit=per_match)
        if picks:
            result[key] = {"videos": [
                {"videoId": p["videoId"], "title": p["title"],
                 "channelTitle": p["channelTitle"],
                 "url": f"https://www.youtube.com/watch?v={p['videoId']}"}
                for p in picks
            ]}
    return result


def main(data_dir="data", api_key=None, fetcher=fetch_text, now_iso=None, allow_channels=None):
    """鍵が無ければ SKIP（0）。鍵があれば終了済み未キャッシュ試合のハイライトを取得。"""
    if api_key is None:
        api_key = os.environ.get("YOUTUBE_API_KEY", "")
    if not api_key:
        print("SKIP: YOUTUBE_API_KEY が未設定のためハイライト取得を省略します。")
        return 0
    structure = read_json_or_none(f"{data_dir}/structure.json")
    if not structure:
        print("SKIP: structure.json が無いためハイライト取得を省略します。", file=sys.stderr)
        return 1
    if now_iso is None:
        now_iso = datetime.now(timezone.utc).isoformat()
    existing = (read_json_or_none(f"{data_dir}/highlights.json") or {}).get("items", {})
    items = fetch_highlights(structure.get("matches", []), api_key, existing=existing,
                             fetcher=fetcher, allow_channels=allow_channels)
    write_json_atomic(f"{data_dir}/highlights.json", {"generated_at": now_iso, "items": items})
    print(f"ハイライト {len(items)} 件を書き込みました: {data_dir}/highlights.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
