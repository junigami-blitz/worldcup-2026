"""data/*.json を読み、site/ に静的HTML（4ページ）と assets を生成する。"""
import shutil
import sys
from pathlib import Path

from wc.atomic_io import read_json_or_none
from wc.i18n import jp_round
from wc.timeutil import parse_iso, to_jst
from wc.render import (
    match_card, standings_table, scorers_table, page_shell, news_list,
    team_stats_table, bracket_match,
)
from wc.teamstats import compute_team_stats

# 決勝トーナメントのラウンド表示順
_KO_ORDER = [
    "Round of 32", "Round of 16", "Quarter-final",
    "Semi-final", "Match for third place", "Final",
]


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
        cards = "".join(match_card(m, tbn, highlights) for m in matches)
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

    body = (
        '<h1 class="page-title">ワールドカップ2026 速報・順位</h1>'
        '<p class="page-lead">カナダ・メキシコ・USA共催。最新の試合結果と順位をお届けします。</p>'
        f'{summary}{today_html}{upcoming_html}{results}'
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
        cards = "".join(match_card(m, tbn, highlights) for m in g_matches)
        match_html = f'<div class="match-list group-matches">{cards}</div>' if cards else ""
        blocks.append(f'<section class="group">{table}{match_html}</section>')

    body = (
        '<h1 class="page-title">グループステージ</h1>'
        '<p class="page-lead">各グループ上位2チームが決勝トーナメントへ進出。各組3位の上位8チームも進出します。</p>'
        f'{_legend()}'
        f'<div class="group-grid">{"".join(blocks)}</div>'
    )
    return body


def build_knockout(structure, highlights=None):
    """決勝トーナメント: 横スクロールのブラケット図（ベスト32→決勝）。3位決定戦は別枠。"""
    tbn = _teams_by_name(structure)
    matches = [m for m in structure.get("matches", []) if m.get("stage") == "knockout"]

    # メインブラケット（3位決定戦を除く）
    bracket_order = [r for r in _KO_ORDER if r != "Match for third place"]
    cols = []
    for rnd in bracket_order:
        rnd_matches = sorted(
            [m for m in matches if m.get("round") == rnd],
            key=lambda m: (m.get("date", ""), m.get("kickoff_utc") or ""),
        )
        if not rnd_matches:
            continue
        cards = "".join(bracket_match(m, tbn, highlights) for m in rnd_matches)
        cols.append(
            '<div class="bracket-round">'
            f'<div class="kick block-kicker">{jp_round(rnd)}</div>'
            f'<div class="bracket-col">{cards}</div>'
            '</div>'
        )

    bracket_html = (
        f'<div class="bracket-scroll"><div class="bracket">{"".join(cols)}</div></div>'
        if cols else '<p class="page-lead">決勝トーナメントの試合はまだありません。</p>'
    )

    # 3位決定戦（別枠）
    third = [m for m in matches if m.get("round") == "Match for third place"]
    third_html = ""
    if third:
        cards = "".join(bracket_match(m, tbn, highlights) for m in third)
        third_html = (
            '<div class="third-place">'
            f'<div class="kick block-kicker">{jp_round("Match for third place")}</div>'
            f'<div class="bracket-col">{cards}</div>'
            '</div>'
        )

    body = (
        '<h1 class="page-title">決勝トーナメント</h1>'
        '<p class="page-lead">ベスト32から決勝までの組み合わせと結果。横にスクロールできます。</p>'
        f'{bracket_html}{third_html}'
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


def main(data_dir="data", out_dir="site", templates_dir="templates"):
    """data/*.json を読み site/ に4ページ＋assetsを生成。structure.json が無ければ 1。"""
    data = Path(data_dir)
    structure = read_json_or_none(data / "structure.json")
    if not structure:
        print("structure.json が見つかりません。先に `python -m wc.update_data` を実行してください。",
              file=sys.stderr)
        return 1
    rankings = read_json_or_none(data / "rankings.json") or {"standings": {}, "scorers": [], "generated_at": ""}
    news = read_json_or_none(data / "news.json") or {"items": [], "generated_at": ""}
    highlights = (read_json_or_none(data / "highlights.json") or {}).get("items", {})
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

    # assets/style.css をコピー
    assets = out / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for asset_name in ("style.css", "favicon.svg"):
        src = Path(templates_dir) / asset_name
        if src.exists():
            shutil.copyfile(src, assets / asset_name)

    print(f"サイト生成完了: {out}/ に {len(pages)} ページ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
