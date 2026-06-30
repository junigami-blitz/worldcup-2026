import json
from pathlib import Path

from wc.build_site import (
    build_index, build_groups, build_knockout, build_rankings, build_news, main,
)

NEWS = {
    "generated_at": "2026-06-30T00:00:00+00:00",
    "items": [
        {"title": "日本決勝T進出", "link": "https://e.com/a", "source": "NHK", "published": "2026-06-29"},
    ],
}

STRUCTURE = {
    "name": "World Cup 2026",
    "generated_at": "2026-06-30T00:00:00+00:00",
    "groups": [
        {"name": "Group A", "teams": ["Mexico", "Japan"]},
        {"name": "Group B", "teams": ["Spain", "Brazil"]},
    ],
    "teams": [
        {"name": "Mexico", "flag_icon": "🇲🇽", "group": "A"},
        {"name": "Japan", "flag_icon": "🇯🇵", "group": "A"},
        {"name": "Spain", "flag_icon": "🇪🇸", "group": "B"},
        {"name": "Brazil", "flag_icon": "🇧🇷", "group": "B"},
    ],
    "matches": [
        {"num": 1, "round": "Matchday 1", "stage": "group", "group": "Group A",
         "date": "2026-06-11", "time_local": "13:00 UTC-6", "kickoff_utc": "2026-06-11T19:00:00+00:00",
         "team1": "Mexico", "team2": "Japan", "played": True, "score": {"ft": [1, 2]},
         "goals1": [{"name": "Lozano", "minute": "30", "penalty": False, "owngoal": False}],
         "goals2": [{"name": "Kubo", "minute": "55", "penalty": False, "owngoal": False},
                    {"name": "Mitoma", "minute": "80", "penalty": False, "owngoal": False}],
         "ground": "Mexico City"},
        {"num": 104, "round": "Final", "stage": "knockout", "group": None,
         "date": "2026-07-19", "time_local": "15:00 UTC-4", "kickoff_utc": "2026-07-19T19:00:00+00:00",
         "team1": "Spain", "team2": "Brazil", "played": False, "score": None,
         "goals1": [], "goals2": [], "ground": "New York"},
        {"num": 76, "round": "Round of 32", "stage": "knockout", "group": None,
         "date": "2026-06-28", "time_local": "12:00 UTC-4", "kickoff_utc": "2026-06-28T16:00:00+00:00",
         "team1": "Japan", "team2": "Brazil", "played": True, "score": {"ft": [0, 3]},
         "goals1": [], "goals2": [], "ground": "Toronto"},
    ],
}

RANKINGS = {
    "generated_at": "2026-06-30T00:00:00+00:00",
    "standings": {
        "Group A": [
            {"pos": 1, "team": "Japan", "played": 1, "win": 1, "draw": 0, "loss": 0,
             "gf": 2, "ga": 1, "gd": 1, "points": 3},
            {"pos": 2, "team": "Mexico", "played": 1, "win": 0, "draw": 0, "loss": 1,
             "gf": 1, "ga": 2, "gd": -1, "points": 0},
        ],
    },
    "scorers": [
        {"name": "Kubo", "team": "Japan", "goals": 1, "penalties": 0},
        {"name": "Mitoma", "team": "Japan", "goals": 1, "penalties": 0},
        {"name": "Lozano", "team": "Mexico", "goals": 1, "penalties": 0},
    ],
}


def test_build_groups_includes_all_groups():
    html = build_groups(STRUCTURE, RANKINGS)
    assert "グループA" in html
    assert "グループB" in html
    assert "日本" in html  # 順位表のチーム名（日本語）


def test_build_knockout_uses_two_sided_bracket():
    html = build_knockout(STRUCTURE)
    assert "bk-stage" in html          # ダークステージ
    assert "bk-side-left" in html and "bk-side-right" in html  # 2サイド
    assert "bk-center" in html         # 中央（決勝）
    assert "3位決定戦" in html
    assert "🏆" in html                # トロフィー


def test_build_knockout_resolves_winners_into_bracket():
    # num付きのR32→R16参照を解決し、勝者がブラケットに出る
    structure = {
        "teams": [{"name": "Canada", "flag_icon": "🇨🇦"},
                  {"name": "South Africa", "flag_icon": "🇿🇦"}],
        "matches": [
            {"num": 73, "stage": "knockout", "round": "Round of 32",
             "team1": "South Africa", "team2": "Canada", "played": True,
             "score": {"ft": [0, 1]}, "goals1": [], "goals2": [],
             "kickoff_utc": "2026-06-28T19:00:00+00:00"},
            {"num": 90, "stage": "knockout", "round": "Round of 16",
             "team1": "Canada", "team2": "W75", "played": False, "score": None,
             "goals1": [], "goals2": [], "kickoff_utc": "2026-07-05T19:00:00+00:00"},
        ],
    }
    html = build_knockout(structure)
    assert "カナダ" in html  # 73の勝者 Canada が日本語で表示


def test_build_rankings_lists_scorers():
    html = build_rankings(RANKINGS, STRUCTURE)
    assert "Kubo" in html
    assert "得点王" in html


def test_build_rankings_includes_team_stats():
    html = build_rankings(RANKINGS, STRUCTURE)
    # チーム得点ランキング（消化済み Mexico 1-2 Japan, R32 Japan 0-3 Brazil から集計）
    assert "チーム得点" in html
    assert "ブラジル" in html  # Brazil は R32 で3得点


def test_build_index_has_summary_and_results():
    html = build_index(STRUCTURE, RANKINGS)
    assert "48" not in html  # サンプルは4チームなので48は出ない（数の妥当性）
    assert "4" in html       # 参加チーム数=4
    # 直近結果に得点者
    assert "Kubo" in html or "日本" in html


def test_build_index_shows_featured_highlights():
    hl = {"2026-06-11|Mexico|Japan": {"url": "https://www.youtube.com/watch?v=zzz"}}
    html = build_index(STRUCTURE, RANKINGS, hl)
    assert "注目のハイライト" in html
    assert "youtube.com/watch?v=zzz" in html


def test_build_index_shows_upcoming_with_jst():
    # 未消化(Final, 2026-07-19 19:00 UTC)が「次の試合」にJST表示される
    html = build_index(STRUCTURE, RANKINGS)
    assert "次の試合" in html
    # 2026-07-19T19:00:00+00:00 -> JST 7/20 04:00
    assert "7/20" in html


def test_build_news_lists_articles():
    html = build_news(NEWS)
    assert "日本決勝T進出" in html
    assert "NHK" in html


def test_main_writes_all_pages(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "structure.json").write_text(json.dumps(STRUCTURE, ensure_ascii=False), encoding="utf-8")
    (data_dir / "rankings.json").write_text(json.dumps(RANKINGS, ensure_ascii=False), encoding="utf-8")
    (data_dir / "news.json").write_text(json.dumps(NEWS, ensure_ascii=False), encoding="utf-8")
    tpl_dir = tmp_path / "templates"
    tpl_dir.mkdir()
    (tpl_dir / "style.css").write_text("/* css */", encoding="utf-8")
    out_dir = tmp_path / "site"

    rc = main(data_dir=str(data_dir), out_dir=str(out_dir), templates_dir=str(tpl_dir))
    assert rc == 0
    for page in ["index.html", "groups.html", "knockout.html", "rankings.html", "news.html"]:
        assert (out_dir / page).exists(), f"{page} が生成されていない"
        assert "<!DOCTYPE html>" in (out_dir / page).read_text(encoding="utf-8")
    assert "日本決勝T進出" in (out_dir / "news.html").read_text(encoding="utf-8")
    assert (out_dir / "assets" / "style.css").read_text(encoding="utf-8") == "/* css */"


def test_main_generates_match_pages_with_highlight_thumb(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "structure.json").write_text(json.dumps(STRUCTURE, ensure_ascii=False), encoding="utf-8")
    (data_dir / "rankings.json").write_text(json.dumps(RANKINGS, ensure_ascii=False), encoding="utf-8")
    # Mexico(1) vs Japan のハイライトを用意（videoId付き）
    highlights = {"generated_at": "x", "items": {
        "2026-06-11|Mexico|Japan": {"videoId": "xyz", "title": "ハイライト動画",
                                    "channelTitle": "FIFA", "url": "https://www.youtube.com/watch?v=xyz"}
    }}
    (data_dir / "highlights.json").write_text(json.dumps(highlights, ensure_ascii=False), encoding="utf-8")
    tpl_dir = tmp_path / "templates"
    tpl_dir.mkdir()
    (tpl_dir / "style.css").write_text("/* css */", encoding="utf-8")
    out_dir = tmp_path / "site"
    rc = main(data_dir=str(data_dir), out_dir=str(out_dir), templates_dir=str(tpl_dir))
    assert rc == 0
    # 個別試合ページが生成される
    assert (out_dir / "matches" / "1.html").exists()
    assert (out_dir / "matches" / "104.html").exists()
    page = (out_dir / "matches" / "1.html").read_text(encoding="utf-8")
    # ハイライトはサムネイル画像＋タイトルで掲載
    assert "img.youtube.com/vi/xyz/mqdefault.jpg" in page
    assert "ハイライト動画" in page
    # 配信サービス
    assert "DAZN" in page and "ABEMA" in page and "NHK ONE" in page
    # グループ一覧のカードは詳細ページへリンク
    groups_html = (out_dir / "groups.html").read_text(encoding="utf-8")
    assert "matches/1.html" in groups_html


def test_main_works_without_news_json(tmp_path):
    # news.json が無くても落ちず news.html を生成する
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "structure.json").write_text(json.dumps(STRUCTURE, ensure_ascii=False), encoding="utf-8")
    (data_dir / "rankings.json").write_text(json.dumps(RANKINGS, ensure_ascii=False), encoding="utf-8")
    tpl_dir = tmp_path / "templates"
    tpl_dir.mkdir()
    (tpl_dir / "style.css").write_text("/* css */", encoding="utf-8")
    out_dir = tmp_path / "site"
    rc = main(data_dir=str(data_dir), out_dir=str(out_dir), templates_dir=str(tpl_dir))
    assert rc == 0
    assert (out_dir / "news.html").exists()


def test_main_returns_1_when_structure_missing(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    rc = main(data_dir=str(data_dir), out_dir=str(tmp_path / "site"), templates_dir=str(tmp_path))
    assert rc == 1


def test_main_is_idempotent(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "structure.json").write_text(json.dumps(STRUCTURE, ensure_ascii=False), encoding="utf-8")
    (data_dir / "rankings.json").write_text(json.dumps(RANKINGS, ensure_ascii=False), encoding="utf-8")
    tpl_dir = tmp_path / "templates"
    tpl_dir.mkdir()
    (tpl_dir / "style.css").write_text("/* css */", encoding="utf-8")
    out_dir = tmp_path / "site"
    rc1 = main(data_dir=str(data_dir), out_dir=str(out_dir), templates_dir=str(tpl_dir))
    first = (out_dir / "index.html").read_text(encoding="utf-8")
    rc2 = main(data_dir=str(data_dir), out_dir=str(out_dir), templates_dir=str(tpl_dir))
    second = (out_dir / "index.html").read_text(encoding="utf-8")
    assert rc1 == 0 and rc2 == 0
    assert first == second
