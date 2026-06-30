"""YouTubeハイライト取得（鍵ゲート方式）。

YOUTUBE_API_KEY が無ければ安全にスキップしパイプラインを止めない。
実検索はクォータ節約のため「終了済みかつ未解決の試合」だけを対象にする想定
（results.json と highlights.json のキャッシュ突き合わせ）。本タスクでは
許可チャンネル選別ロジック（純粋関数）と鍵ゲートのスキャフォールドを提供する。
"""
import os
import sys
from urllib.parse import quote

_SEARCH_ENDPOINT = "https://www.googleapis.com/youtube/v3/search"


def pick_highlight(items, allow_channels):
    """検索結果から許可チャンネル優先で1件を選ぶ。許可外しか無ければ None。

    allow_channels は優先順位順（公式 → 放送局 …）。
    誤った非公式動画を載せないよう、許可リストに無いチャンネルは採用しない。
    """
    by_channel = {}
    for it in items or []:
        by_channel.setdefault(it.get("channelId"), it)
    for ch in allow_channels:
        if ch in by_channel:
            return by_channel[ch]
    return None


def build_search_url(query, api_key, max_results=5):
    """YouTube Data API v3 の検索URLを組み立てる。"""
    return (
        f"{_SEARCH_ENDPOINT}?part=snippet&type=video&maxResults={max_results}"
        f"&q={quote(query)}&key={api_key}"
    )


def main(out_dir="data", api_key=None):
    """鍵が無ければ SKIP して 0 を返す（後続のビルドを止めない）。

    鍵がある場合の実検索は results.json の終了済み試合に対して行う想定
    （未解決分のみ検索しキャッシュ）。鍵登録後に拡張する。
    """
    if api_key is None:
        api_key = os.environ.get("YOUTUBE_API_KEY", "")
    if not api_key:
        print("SKIP: YOUTUBE_API_KEY が未設定のためハイライト取得を省略します。")
        return 0
    # 鍵あり時の実装は鍵登録後に拡張（results.json突き合わせ→未解決のみ検索）
    print("YOUTUBE_API_KEY 検出。ハイライト検索は次フェーズで実装します。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
