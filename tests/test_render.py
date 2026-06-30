from wc.render import (
    flag, goal_line, match_card, standings_table, scorers_table, page_shell,
    news_list, team_stats_table, bracket_node, highlight_strip,
)

TEAMS = {
    "Japan": {"name": "Japan", "flag_icon": "🇯🇵"},
    "Spain": {"name": "Spain", "flag_icon": "🇪🇸"},
    "Côte": {"name": "Côte", "flag_icon": ""},
}


def test_flag_wraps_emoji():
    assert flag("🇯🇵") == '<span class="flag">🇯🇵</span>'


def test_flag_empty_returns_empty():
    assert flag("") == ""
    assert flag(None) == ""


def test_goal_line_formats_scorers():
    g1 = [{"name": "Kubo", "minute": "41", "penalty": False, "owngoal": False}]
    g2 = [{"name": "Pedri", "minute": "78", "penalty": True, "owngoal": False}]
    line = goal_line(g1, g2)
    assert "Kubo" in line
    assert "41" in line
    assert "Pedri" in line
    assert "PK" in line  # ペナルティ表示


def test_goal_line_empty_when_no_goals():
    assert goal_line([], []) == ""


def test_goal_line_escapes_names():
    g1 = [{"name": "<script>", "minute": "10", "penalty": False, "owngoal": False}]
    line = goal_line(g1, [])
    assert "<script>" not in line
    assert "&lt;script&gt;" in line


def test_match_card_played_shows_score_and_jp_names():
    m = {
        "team1": "Japan", "team2": "Spain", "played": True,
        "score": {"ft": [2, 1]}, "goals1": [], "goals2": [],
        "date": "2026-06-27", "time_local": "13:00 UTC-6", "round": "Matchday 2",
    }
    html = match_card(m, TEAMS)
    assert "日本" in html
    assert "スペイン" in html
    assert "2" in html and "1" in html
    assert "🇯🇵" in html


def test_match_card_shows_highlight_link_when_present():
    m = {
        "team1": "Japan", "team2": "Spain", "played": True,
        "score": {"ft": [2, 1]}, "goals1": [], "goals2": [],
        "date": "2026-06-27", "time_local": "13:00 UTC-6", "round": "Matchday 2",
    }
    highlights = {"2026-06-27|Japan|Spain": {"url": "https://www.youtube.com/watch?v=abc"}}
    html = match_card(m, TEAMS, highlights)
    assert "ハイライト" in html
    assert "youtube.com/watch?v=abc" in html


def test_match_card_no_highlight_link_when_absent():
    m = {
        "team1": "Japan", "team2": "Spain", "played": True,
        "score": {"ft": [2, 1]}, "goals1": [], "goals2": [],
        "date": "2026-06-27", "time_local": "13:00 UTC-6", "round": "Matchday 2",
    }
    html = match_card(m, TEAMS, {})  # ハイライトなし
    assert "ハイライト" not in html


def test_match_card_unplayed_shows_vs():
    m = {
        "team1": "Japan", "team2": "Spain", "played": False,
        "score": None, "goals1": [], "goals2": [],
        "date": "2026-06-27", "time_local": "13:00 UTC-6", "round": "Matchday 2",
    }
    html = match_card(m, TEAMS)
    assert "vs" in html.lower()


def test_match_card_unplayed_shows_jst_kickoff():
    m = {
        "team1": "Japan", "team2": "Spain", "played": False,
        "score": None, "goals1": [], "goals2": [],
        "date": "2026-06-27", "time_local": "13:00 UTC-6",
        "kickoff_utc": "2026-06-11T19:00:00+00:00", "round": "Matchday 2",
    }
    html = match_card(m, TEAMS)
    # 日本時間のキックオフ（19:00 UTC -> 翌04:00 JST）を表示
    assert "04:00" in html
    assert "6/12" in html


def test_standings_table_marks_advance_line():
    rows = [
        {"pos": 1, "team": "Japan", "played": 2, "win": 2, "draw": 0, "loss": 0,
         "gf": 4, "ga": 1, "gd": 3, "points": 6},
        {"pos": 2, "team": "Spain", "played": 2, "win": 1, "draw": 0, "loss": 1,
         "gf": 2, "ga": 2, "gd": 0, "points": 3},
        {"pos": 3, "team": "Côte", "played": 2, "win": 0, "draw": 0, "loss": 2,
         "gf": 0, "ga": 3, "gd": -3, "points": 0},
    ]
    html = standings_table("グループE", rows, TEAMS)
    assert "グループE" in html
    assert "日本" in html
    # 上位2チームは突破ライン(is-advance)
    assert html.count("is-advance") == 2
    assert "6" in html


def test_scorers_table_lists_top():
    scorers = [
        {"name": "Mbappe", "team": "France", "goals": 5, "penalties": 1},
        {"name": "Kane", "team": "England", "goals": 3, "penalties": 0},
    ]
    html = scorers_table(scorers, top_n=10)
    assert "Mbappe" in html
    assert "5" in html
    assert "フランス" in html  # チーム名は日本語化


def test_scorers_table_respects_top_n():
    scorers = [{"name": f"P{i}", "team": "Japan", "goals": 10 - i, "penalties": 0}
               for i in range(20)]
    html = scorers_table(scorers, top_n=5)
    assert "P0" in html
    assert "P5" not in html  # 6番目以降は出さない


def test_bracket_node_played_marks_winner():
    m = {"team1": "Japan", "team2": "Spain", "played": True, "score": {"ft": [2, 1]},
         "date": "2026-06-28", "kickoff_utc": "2026-06-28T16:00:00+00:00"}
    html = bracket_node(m, TEAMS)
    assert "日本" in html and "スペイン" in html
    assert "bk-node" in html
    assert "is-win" in html  # 勝者(日本)行にマーカー


def test_bracket_node_unplayed_placeholder_is_dim():
    m = {"team1": "W74", "team2": "W77", "played": False, "score": None,
         "kickoff_utc": "2026-07-05T19:00:00+00:00"}
    html = bracket_node(m, TEAMS)
    assert "W74" in html
    assert "is-tbd" in html  # 未確定は淡色クラス
    assert "is-win" not in html


def test_bracket_node_none_is_empty():
    assert "is-empty" in bracket_node(None, TEAMS)


def test_team_stats_table_renders_jp_and_values():
    rows = [
        {"team": "Japan", "played": 3, "gf": 7, "ga": 2, "gd": 5},
        {"team": "Spain", "played": 3, "gf": 4, "ga": 4, "gd": 0},
    ]
    html = team_stats_table(rows, TEAMS, top_n=10)
    assert "日本" in html
    assert "7" in html
    assert "+5" in html


def test_team_stats_table_respects_top_n():
    rows = [{"team": f"T{i}", "played": 1, "gf": 10 - i, "ga": 0, "gd": 10 - i} for i in range(10)]
    html = team_stats_table(rows, {}, top_n=3)
    assert "T0" in html
    assert "T3" not in html


def test_news_list_renders_items_and_escapes():
    items = [
        {"title": "日本勝利 <速報>", "link": "https://e.com/a", "source": "NHK", "published": "2026-06-29"},
        {"title": "メッシ得点", "link": "https://e.com/b", "source": "スポニチ", "published": "2026-06-28"},
    ]
    html = news_list(items, limit=10)
    assert "日本勝利" in html
    assert "<速報>" not in html and "&lt;速報&gt;" in html  # エスケープ
    assert 'href="https://e.com/a"' in html
    assert "NHK" in html


def test_news_list_empty_returns_message():
    html = news_list([], limit=10)
    assert "ニュース" in html  # 「ニュースはありません」等のメッセージ


def test_news_list_respects_limit():
    items = [{"title": f"記事{i}", "link": f"https://e.com/{i}", "source": "X", "published": "2026-06-30"}
             for i in range(10)]
    html = news_list(items, limit=3)
    assert "記事0" in html
    assert "記事3" not in html


def test_page_shell_sets_active_tab_and_links_css():
    html = page_shell("テスト", "groups", "<p>body</p>", "2026-06-30T00:00:00+00:00")
    assert "<!DOCTYPE html>" in html
    assert 'lang="ja"' in html
    assert "assets/style.css" in html
    assert "<p>body</p>" in html
    # アクティブタブにマーカー
    assert "is-active" in html


def test_page_shell_has_seo_and_ogp():
    html = page_shell("グループ", "groups", "<p>b</p>", "2026-06-30T00:00:00+00:00",
                      description="グループ順位表", path="groups.html")
    # メタdescription
    assert '<meta name="description" content="グループ順位表">' in html
    # OGP
    assert 'property="og:title"' in html
    assert 'property="og:description"' in html
    assert 'property="og:url"' in html
    assert 'property="og:type"' in html
    assert 'name="twitter:card"' in html
    # canonical（絶対URL）
    assert '<link rel="canonical"' in html
    assert "junigami-blitz.github.io/worldcup-2026/groups.html" in html


def test_page_shell_escapes_description():
    html = page_shell("t", "index", "<p>b</p>", "x", description='a"<b>')
    assert 'a"<b>' not in html.split("<body>")[0] or "&quot;" in html  # 属性内エスケープ


def test_page_shell_footer_shows_jst():
    html = page_shell("t", "index", "<p>b</p>", "2026-06-30T10:00:00+00:00")
    # 10:00 UTC -> 19:00 JST
    assert "JST" in html
    assert "19:00" in html


def test_highlight_strip_lists_only_with_highlights():
    matches = [
        {"date": "2026-06-27", "team1": "Japan", "team2": "Spain",
         "played": True, "score": {"ft": [2, 1]}},
        {"date": "2026-06-26", "team1": "Japan", "team2": "Côte",
         "played": True, "score": {"ft": [0, 3]}},
    ]
    hl = {"2026-06-27|Japan|Spain": {"url": "https://www.youtube.com/watch?v=abc"}}
    html = highlight_strip(matches, TEAMS, hl, limit=4)
    assert "日本" in html
    assert "youtube.com/watch?v=abc" in html
    assert "ハイライト" in html


def test_highlight_strip_empty_when_none():
    matches = [{"date": "2026-06-27", "team1": "Japan", "team2": "Spain",
                "played": True, "score": {"ft": [2, 1]}}]
    assert highlight_strip(matches, TEAMS, {}, limit=4) == ""


def test_page_shell_index_has_jsonld():
    html = page_shell("トップ", "index", "<p>b</p>", "2026-06-30T00:00:00+00:00",
                      path="index.html", jsonld=True)
    assert "application/ld+json" in html
    assert "SportsEvent" in html
