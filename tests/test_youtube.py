from wc.youtube import pick_highlight, build_search_url, main


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


def test_pick_empty_returns_none():
    assert pick_highlight([], ALLOW) is None


def test_build_search_url_includes_key_and_query():
    url = build_search_url("日本 ハイライト", "KEY123")
    assert "key=KEY123" in url
    assert "q=" in url
    assert "googleapis.com" in url


def test_main_skips_without_api_key(capsys):
    rc = main(api_key="")  # 鍵未設定
    assert rc == 0  # パイプラインを止めない
    out = capsys.readouterr().out
    assert "SKIP" in out
