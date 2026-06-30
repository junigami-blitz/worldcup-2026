import json

from wc.youtube import (
    pick_highlight, build_search_url, parse_search_results,
    fetch_highlights, search_query, main,
)


def _item(vid, channel_id, title="HL"):
    return {"videoId": vid, "channelId": channel_id, "channelTitle": "ch", "title": title}


# 許可チャンネル（優先順位順: 公式 → 放送局）
ALLOW = ["UC_FIFA_OFFICIAL", "UC_BROADCASTER"]


def test_pick_prefers_higher_priority_channel():
    items = [
        _item("v1", "UC_BROADCASTER"),
        _item("v2", "UC_FIFA_OFFICIAL"),
        _item("v3", "UC_RANDOM"),
    ]
    picked = pick_highlight(items, ALLOW)
    assert picked["videoId"] == "v2"  # 公式が最優先


def test_pick_falls_back_to_next_allowed():
    items = [_item("v1", "UC_BROADCASTER"), _item("v3", "UC_RANDOM")]
    picked = pick_highlight(items, ALLOW)
    assert picked["videoId"] == "v1"  # 公式が無ければ放送局


def test_pick_returns_none_when_no_allowed_channel():
    items = [_item("v1", "UC_RANDOM"), _item("v2", "UC_OTHER")]
    assert pick_highlight(items, ALLOW) is None  # 許可外は採用しない（誤動画防止）


def test_pick_empty_allow_returns_first():
    items = [_item("v1", "UC_RANDOM"), _item("v2", "UC_OTHER")]
    # 許可リスト未設定時は先頭（最も関連度が高い検索結果）を採用
    assert pick_highlight(items, [])["videoId"] == "v1"


def test_pick_empty_items_returns_none():
    assert pick_highlight([], ALLOW) is None
    assert pick_highlight([], []) is None


def test_build_search_url_includes_key_and_query():
    url = build_search_url("日本 ハイライト", "KEY123")
    assert "key=KEY123" in url
    assert "q=" in url
    assert "googleapis.com" in url


def test_search_query_contains_teams():
    q = search_query({"team1": "Japan", "team2": "Brazil"})
    assert "Japan" in q and "Brazil" in q


SEARCH_JSON = json.dumps({
    "items": [
        {"id": {"videoId": "abc"},
         "snippet": {"channelId": "UC_FIFA_OFFICIAL", "channelTitle": "FIFA", "title": "Japan vs Brazil"}},
        {"id": {"videoId": "def"},
         "snippet": {"channelId": "UC_RANDOM", "channelTitle": "Fan", "title": "reupload"}},
    ]
})


def test_parse_search_results():
    items = parse_search_results(SEARCH_JSON)
    assert items[0] == {"videoId": "abc", "channelId": "UC_FIFA_OFFICIAL",
                        "channelTitle": "FIFA", "title": "Japan vs Brazil"}


def test_parse_search_results_broken_returns_empty():
    assert parse_search_results("<not json") == []


def test_fetch_highlights_skips_cached_and_unplayed():
    matches = [
        {"date": "2026-06-11", "team1": "Japan", "team2": "Brazil", "played": True},
        {"date": "2026-06-12", "team1": "Spain", "team2": "Italy", "played": True},
        {"date": "2026-07-01", "team1": "A", "team2": "B", "played": False},  # 未消化→検索しない
    ]
    existing = {"2026-06-11|Japan|Brazil": {"videoId": "cached"}}  # 既存はスキップ
    calls = []

    def fake_fetcher(url):
        calls.append(url)
        return SEARCH_JSON

    result = fetch_highlights(matches, "KEY", existing=existing,
                              fetcher=fake_fetcher, allow_channels=ALLOW)
    # 既存のJapan戦はそのまま、未消化は検索しない、Spain戦のみ新規検索
    assert result["2026-06-11|Japan|Brazil"]["videoId"] == "cached"
    assert result["2026-06-12|Spain|Italy"]["videoId"] == "abc"
    assert len(calls) == 1  # Spain戦の1回だけ検索


def test_fetch_highlights_respects_max_searches():
    matches = [{"date": f"2026-06-{10+i}", "team1": f"T{i}", "team2": "X", "played": True}
               for i in range(5)]

    def fake_fetcher(url):
        return SEARCH_JSON

    result = fetch_highlights(matches, "KEY", existing={}, fetcher=fake_fetcher,
                              allow_channels=ALLOW, max_searches=2)
    assert len(result) == 2  # 上限2件で打ち切り（クォータ節約）


def test_main_skips_without_api_key(capsys):
    rc = main(api_key="")  # 鍵未設定
    assert rc == 0  # パイプラインを止めない
    assert "SKIP" in capsys.readouterr().out


def test_main_writes_highlights_with_key(tmp_path):
    structure = {
        "matches": [
            {"date": "2026-06-11", "team1": "Japan", "team2": "Brazil", "played": True},
        ]
    }
    (tmp_path / "structure.json").write_text(json.dumps(structure), encoding="utf-8")

    rc = main(data_dir=str(tmp_path), api_key="KEY", fetcher=lambda url: SEARCH_JSON,
              now_iso="2026-06-30T00:00:00+00:00", allow_channels=ALLOW)
    assert rc == 0
    data = json.loads((tmp_path / "highlights.json").read_text(encoding="utf-8"))
    assert data["items"]["2026-06-11|Japan|Brazil"]["videoId"] == "abc"
    assert "youtube.com/watch?v=abc" in data["items"]["2026-06-11|Japan|Brazil"]["url"]
