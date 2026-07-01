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
from wc.i18n import jp_team

_SEARCH_ENDPOINT = "https://www.googleapis.com/youtube/v3/search"

# 許可チャンネル（優先順位順）。日本語ハイライトを優先するため日本の公式チャンネルを既定にする。
# 未ヒット時はソフトフォールバック（下記 pick_highlights の fallback）で検索上位を採用し、
# 動画カードが空になるのを防ぐ。channelId は externalId で実在確認済み。
DEFAULT_ALLOW_CHANNELS = [
    "UCoFLB_Gw_AoxUuuzKjXrc_Q",  # DAZN Japan（筆頭）
    "UCRZfD9OSko3knCyy-Ccngsw",  # NHK SPORTS
    "UCi19rPu3Py74nghR7UD4H9w",  # JFA TV（日本サッカー協会）
    "UC7_mFzmj89tqAqgpl5695QQ",  # フジテレビ公式
]

# 検索の日本語バイアス（日本リージョン・日本語の結果を上位化）
DEFAULT_REGION_CODE = "JP"
DEFAULT_RELEVANCE_LANGUAGE = "ja"

# 1回の実行で行う検索の上限（無料枠1万ユニット/日＝検索100回/日、検索100ユニット/回）。
# 90 は消化済み試合の一括バックフィルを1回で賄いつつ日次クォータに余裕を残す値。
# 以降はキャッシュにより新規試合のみ検索するため実消費は小さい。
DEFAULT_MAX_SEARCHES = 90


def pick_highlight(items, allow_channels):
    """検索結果から1件を選ぶ（後方互換）。許可外しか無ければ None。"""
    picks = pick_highlights(items, allow_channels, limit=1)
    return picks[0] if picks else None


def pick_highlights(items, allow_channels, limit=4, fallback=False):
    """検索結果から最大 limit 件を選ぶ。

    allow_channels が空なら関連度上位から limit 件。
    指定時は許可チャンネルのみを優先順位順に採用（誤動画防止）。
    fallback=True の場合、許可チャンネルにヒットが無ければ検索上位で補充する
    （日本語バイアス済みの検索結果で埋め、ゼロ件になるのを防ぐ）。
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
    if not wl and fallback:
        return items[:limit]
    return wl[:limit]


def search_query(match):
    """試合からYouTube検索クエリを組み立てる（日本語化して日本チャンネルを狙う）。"""
    t1 = jp_team(match.get("team1", ""))
    t2 = jp_team(match.get("team2", ""))
    return f"{t1} 対 {t2} ハイライト ワールドカップ 2026"


def build_search_url(query, api_key, max_results=5,
                     region_code=DEFAULT_REGION_CODE,
                     relevance_language=DEFAULT_RELEVANCE_LANGUAGE):
    """YouTube Data API v3 の検索URLを組み立てる。

    region_code / relevance_language で日本語バイアスをかける（None で無効化）。
    """
    url = (
        f"{_SEARCH_ENDPOINT}?part=snippet&type=video&maxResults={max_results}"
        f"&q={quote(query)}&key={api_key}"
    )
    if region_code:
        url += f"&regionCode={region_code}"
    if relevance_language:
        url += f"&relevanceLanguage={relevance_language}"
    return url


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
                     allow_channels=None, max_searches=DEFAULT_MAX_SEARCHES, per_match=4,
                     fallback=True):
    """終了済みかつ未キャッシュの試合だけ検索し、{key:{videos:[...]}} を返す。

    各試合 per_match 本まで保持。既存キャッシュ（videos済）は保持。
    max_searches で1回の検索回数を制限。
    fallback=True（既定）は許可チャンネル未ヒット時に検索上位で補充する。
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
        picks = pick_highlights(results, allow, limit=per_match, fallback=fallback)
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
