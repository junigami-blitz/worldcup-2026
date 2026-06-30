"""data/*.json を読み、site/ に静的HTML（4ページ）と assets を生成する。"""
import shutil
import sys
from pathlib import Path

from wc.atomic_io import read_json_or_none
from wc.i18n import jp_round
from wc.timeutil import parse_iso, to_jst
from wc.render import (
    match_card, standings_table, scorers_table, page_shell, news_list,
    team_stats_table, bracket_node, highlight_strip, match_detail,
)
from wc.i18n import jp_team
from wc.matchid import match_key
from wc.teamstats import compute_team_stats
from wc.bracket import resolve_bracket
from wc.squads import squads_by_team

# WC2026 決勝トーナメントの固定ブラケット配置（試合番号で指定）。
# 左サイド = 準決勝101の枝、右サイド = 準決勝102の枝。各列は外側→内側、
# 縦並びは上から（隣接2つが次のラウンドのペアになる順）。
_LEFT_COLUMNS = [
    ("ベスト32", [74, 77, 73, 75, 83, 84, 81, 82]),
    ("ベスト16", [89, 90, 93, 94]),
    ("準々決勝", [97, 98]),
    ("準決勝", [101]),
]
_RIGHT_COLUMNS = [
    ("準決勝", [102]),
    ("準々決勝", [99, 100]),
    ("ベスト16", [91, 92, 95, 96]),
    ("ベスト32", [76, 78, 79, 80, 86, 88, 85, 87]),
]
_FINAL_NUM = 104
_THIRD_NUM = 103


def _teams_by_name(structure):
    return {t["name"]: t for t in structure.get("teams", [])}


def _jp_group(group_name):
    """"Group A" → "グループA"。"""
    return (group_name or "").replace("Group ", "グループ")


def _legend():
    return (
        '<div class="legend">'
        '<span><span class="swatch adv"></span>決勝トーナメント進出</span>'
        '<span><span class="swatch po"></span>3位（上位8チーム進出の可能性）</span>'
        '</div>'
    )


def build_index(structure, rankings, highlights=None):
    """トップ: 大会サマリー＋直近の結果カード。"""
    tbn = _teams_by_name(structure)
    matches = structure.get("matches", [])
    played = [m for m in matches if m.get("played")]
    n_teams = len(structure.get("teams", []))
    n_groups = len(structure.get("groups", []))

    summary = (
        '<div class="summary">'
        f'<div class="cell"><div class="k kick">Teams</div><div class="v num">{n_teams}</div></div>'
        f'<div class="cell"><div class="k kick">Groups</div><div class="v num">{n_groups}</div></div>'
        f'<div class="cell"><div class="k kick">Played</div><div class="v num">{len(played)}</div></div>'
        f'<div class="cell"><div class="k kick">Total</div><div class="v num">{len(matches)}</div></div>'
        '</div>'
    )

    # 「現在時刻」は generated_at を基準にする
    now = parse_iso(structure.get("generated_at", "")) or parse_iso(rankings.get("generated_at", ""))
    now_jst_date = to_jst(structure.get("generated_at", "")).date() if now else None

    def _section(title, matches):
        if not matches:
            return ""
        cards = "".join(match_card(m, tbn) for m in matches)
        return (
            f'<div class="kick section-kicker">{title}</div>'
            f'<div class="match-list">{cards}</div>'
        )

    today_html = upcoming_html = ""
    if now is not None:
        # 本日の試合（JSTの同日キックオフ）
        todays = [m for m in matches
                  if m.get("kickoff_utc") and to_jst(m["kickoff_utc"]).date() == now_jst_date]
        todays.sort(key=lambda m: m["kickoff_utc"])
        today_html = _section("本日の試合", todays)

        # 次の試合（現在以降のキックオフ。本日分を除く最大6件）
        future = [m for m in matches
                  if m.get("kickoff_utc") and parse_iso(m["kickoff_utc"]) > now
                  and to_jst(m["kickoff_utc"]).date() != now_jst_date]
        future.sort(key=lambda m: m["kickoff_utc"])
        upcoming_html = _section("次の試合", future[:6])

    # 直近の結果＝消化済み試合のうち日付が新しい順に最大8件
    recent = sorted(played, key=lambda m: m.get("date", ""), reverse=True)[:8]
    results = _section("最近の試合結果", recent) or \
        '<p class="page-lead">まだ消化された試合はありません。</p>'

    # 注目のハイライト（直近の消化試合のうちハイライトがあるもの）
    recent_all = sorted(played, key=lambda m: m.get("date", ""), reverse=True)
    featured = highlight_strip(recent_all, tbn, highlights, limit=4)

    body = (
        '<h1 class="page-title">ワールドカップ2026 速報・順位</h1>'
        '<p class="page-lead">カナダ・メキシコ・USA共催。最新の試合結果と順位をお届けします。</p>'
        f'{summary}{featured}{today_html}{upcoming_html}{results}'
    )
    return body


def build_groups(structure, rankings, highlights=None):
    """グループステージ: 12グループの順位表＋各グループの試合カード。"""
    tbn = _teams_by_name(structure)
    standings = rankings.get("standings", {})
    matches = structure.get("matches", [])

    blocks = []
    for g in structure.get("groups", []):
        gname = g["name"]
        label = _jp_group(gname)
        rows = standings.get(gname, [])
        table = standings_table(label, rows, tbn) if rows else (
            f'<div class="standings-block"><div class="kick block-kicker">{label}</div>'
            '<p class="page-lead">順位データはまだありません。</p></div>'
        )
        # このグループの試合（日付順）
        g_matches = sorted(
            [m for m in matches if m.get("stage") == "group" and m.get("group") == gname],
            key=lambda m: (m.get("date", ""), m.get("kickoff_utc") or ""),
        )
        cards = "".join(match_card(m, tbn) for m in g_matches)
        match_html = f'<div class="match-list group-matches">{cards}</div>' if cards else ""
        blocks.append(f'<section class="group">{table}{match_html}</section>')

    body = (
        '<h1 class="page-title">グループステージ</h1>'
        '<p class="page-lead">各グループ上位2チームが決勝トーナメントへ進出。各組3位の上位8チームも進出します。</p>'
        f'{_legend()}'
        f'<div class="group-grid">{"".join(blocks)}</div>'
    )
    return body


def _bk_side(columns, by_num, tbn, side):
    """片側（左/右）のブラケット列群を生成。"""
    cols = []
    for label, nums in columns:
        nodes = "".join(bracket_node(by_num.get(n), tbn) for n in nums)
        cols.append(
            f'<div class="bk-col" data-round="{label}">'
            f'<div class="bk-col-label kick">{label}</div>'
            f'<div class="bk-col-body">{nodes}</div>'
            '</div>'
        )
    return f'<div class="bk-side bk-side-{side}">{"".join(cols)}</div>'


def build_knockout(structure, highlights=None):
    """決勝トーナメント: 左右から中央の決勝へ集約する2サイド・ブラケット図。"""
    tbn = _teams_by_name(structure)
    ko = [m for m in structure.get("matches", []) if m.get("stage") == "knockout"]
    if not ko:
        return ('<h1 class="page-title">決勝トーナメント</h1>'
                '<p class="page-lead">決勝トーナメントの試合はまだありません。</p>')

    by_num = resolve_bracket(ko)

    left = _bk_side(_LEFT_COLUMNS, by_num, tbn, "left")
    right = _bk_side(_RIGHT_COLUMNS, by_num, tbn, "right")

    final_node = bracket_node(by_num.get(_FINAL_NUM), tbn)
    third_node = bracket_node(by_num.get(_THIRD_NUM), tbn)
    center = (
        '<div class="bk-center">'
        '<div class="bk-col-label kick bk-final-label">決勝</div>'
        f'<div class="bk-final">{final_node}</div>'
        '<div class="bk-trophy">🏆</div>'
        '<div class="bk-col-label kick bk-third-label">3位決定戦</div>'
        f'<div class="bk-third">{third_node}</div>'
        '</div>'
    )

    stage = (
        '<div class="bk-stage">'
        '<div class="bk-stage-head">'
        '<div class="bk-stage-title kick">FIFA WORLD CUP 2026</div>'
        '<div class="bk-stage-sub">決勝トーナメント</div>'
        '</div>'
        '<div class="bk-scroll"><div class="bk-board">'
        f'{left}{center}{right}'
        '</div></div>'
        '</div>'
    )

    body = (
        '<h1 class="page-title">決勝トーナメント</h1>'
        '<p class="page-lead">ベスト32から決勝までの組み合わせと結果。横にスクロールできます。</p>'
        f'{stage}'
    )
    return body


def build_rankings(rankings, structure=None):
    """ランキング: 得点王＋チーム得点/失点ランキング。"""
    scorers = rankings.get("scorers", [])
    if scorers:
        scorer_table = scorers_table(scorers, top_n=25)
    else:
        scorer_table = '<p class="page-lead">得点データはまだありません。</p>'

    team_section = ""
    if structure:
        tbn = _teams_by_name(structure)
        stats = compute_team_stats(structure.get("matches", []))
        if stats:
            team_section = (
                '<h2 class="page-title" style="margin-top:42px;">チーム得点ランキング</h2>'
                '<p class="page-lead">消化済み全試合からの総得点・失点・得失点差。</p>'
                f'{team_stats_table(stats, tbn, top_n=48)}'
            )

    body = (
        '<h1 class="page-title">得点王ランキング</h1>'
        '<p class="page-lead">大会を通じた得点数の上位選手（PKは内訳として併記）。</p>'
        f'{scorer_table}{team_section}'
    )
    return body


def build_news(news):
    """ニュース: Google News RSS の記事一覧。"""
    items = (news or {}).get("items", [])
    body = (
        '<h1 class="page-title">ニュース</h1>'
        '<p class="page-lead">「ワールドカップ2026」関連の最新ニュース（Google ニュース・日本語）。</p>'
        f'{news_list(items, limit=30)}'
    )
    return body


def _resolved_matches_by_num(structure):
    """全試合を num→試合dict に。ノックアウトは W/L 参照を実チーム名へ解決する。"""
    all_matches = structure.get("matches", [])
    ko = [m for m in all_matches if m.get("stage") == "knockout"]
    resolved = resolve_bracket(ko)
    out = {}
    for m in all_matches:
        num = m.get("num")
        if num is None:
            continue
        if m.get("stage") == "knockout" and num in resolved:
            out[num] = {**m, "team1": resolved[num]["team1"], "team2": resolved[num]["team2"]}
        else:
            out[num] = m
    return out


def _write_match_pages(structure, highlights, news_items, squads_by_name, goals_by_name,
                       lineups, gen, out):
    """各試合の個別ページを site/matches/{num}.html に生成。生成数を返す。"""
    tbn = _teams_by_name(structure)
    by_num = _resolved_matches_by_num(structure)
    mdir = out / "matches"
    mdir.mkdir(parents=True, exist_ok=True)
    for num, m in by_num.items():
        hl = highlights.get(match_key(m))
        md = lineups.get(match_key(m))
        n1, n2 = jp_team(m.get("team1", "")), jp_team(m.get("team2", ""))
        title = f"{n1} vs {n2}"
        desc = f"ワールドカップ2026 {title} の日程・結果・スタメン・スタッツ・ハイライト動画・関連ニュース・日本での配信(DAZN/ABEMA/NHK ONE)。"
        body = match_detail(m, tbn, hl, news_items=news_items, squads_by_name=squads_by_name,
                            goals_by_name=goals_by_name, match_data=md, gen=gen, base="../")
        html = page_shell(title, None, body, gen, description=desc,
                          path=f"matches/{num}.html", base="../")
        (mdir / f"{num}.html").write_text(html, encoding="utf-8")
    return len(by_num)


def main(data_dir="data", out_dir="site", templates_dir="templates"):
    """data/*.json を読み site/ にページ群＋個別試合ページ＋assetsを生成。"""
    data = Path(data_dir)
    structure = read_json_or_none(data / "structure.json")
    if not structure:
        print("structure.json が見つかりません。先に `python -m wc.update_data` を実行してください。",
              file=sys.stderr)
        return 1
    rankings = read_json_or_none(data / "rankings.json") or {"standings": {}, "scorers": [], "generated_at": ""}
    news = read_json_or_none(data / "news.json") or {"items": [], "generated_at": ""}
    highlights = (read_json_or_none(data / "highlights.json") or {}).get("items", {})
    squads = squads_by_team((read_json_or_none(data / "squads.json") or {}).get("teams", []))
    lineups = (read_json_or_none(data / "lineups.json") or {}).get("items", {})
    goals_by_name = {s["name"]: s["goals"] for s in rankings.get("scorers", [])}
    gen = structure.get("generated_at", rankings.get("generated_at", ""))

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    pages = {
        "index.html": ("トップ", "index", build_index(structure, rankings, highlights),
                       "FIFAワールドカップ2026の最新結果・順位・得点王・ニュース・ハイライトを日本語で速報。", True),
        "groups.html": ("グループ", "groups", build_groups(structure, rankings, highlights),
                        "ワールドカップ2026 全12グループの順位表・日程・結果。各組上位2チームが決勝トーナメント進出。", False),
        "knockout.html": ("決勝トーナメント", "knockout", build_knockout(structure, highlights),
                          "ワールドカップ2026 決勝トーナメント（ベスト32〜決勝）の組み合わせと結果のブラケット。", False),
        "rankings.html": ("ランキング", "rankings", build_rankings(rankings, structure),
                          "ワールドカップ2026 得点王ランキングとチーム得点・失点ランキング。", False),
        "news.html": ("ニュース", "news", build_news(news),
                      "ワールドカップ2026関連の最新ニュース（日本語）。", False),
    }
    for filename, (title, active, body, desc, jsonld) in pages.items():
        html = page_shell(title, active, body, gen, description=desc, path=filename, jsonld=jsonld)
        (out / filename).write_text(html, encoding="utf-8")

    # 個別試合ページ
    n_matches = _write_match_pages(structure, highlights, news.get("items", []),
                                   squads, goals_by_name, lineups, gen, out)

    # assets/style.css をコピー
    assets = out / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for asset_name in ("style.css", "favicon.svg"):
        src = Path(templates_dir) / asset_name
        if src.exists():
            shutil.copyfile(src, assets / asset_name)

    print(f"サイト生成完了: {out}/ に {len(pages)} ページ + 試合 {n_matches} ページ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
