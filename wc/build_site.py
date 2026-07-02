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


def build_index(structure, rankings, highlights=None, news=None):
    """トップ: ヒーロー → 本日の試合 → 次の試合(スライダー) → 直近ハイライト → ニュース10件。"""
    from wc.render import match_slider, section_head, hero_section
    tbn = _teams_by_name(structure)
    matches = structure.get("matches", [])
    played = [m for m in matches if m.get("played")]

    # 「現在時刻」は generated_at を基準にする
    now = parse_iso(structure.get("generated_at", "")) or parse_iso(rankings.get("generated_at", ""))
    now_jst_date = to_jst(structure.get("generated_at", "")).date() if now else None

    today_html = upcoming_html = ""
    if now is not None:
        # ① 本日の試合（JSTの同日キックオフ）
        todays = [m for m in matches
                  if m.get("kickoff_utc") and to_jst(m["kickoff_utc"]).date() == now_jst_date]
        todays.sort(key=lambda m: m["kickoff_utc"])
        if todays:
            cards = "".join(match_card(m, tbn) for m in todays)
            today_html = (section_head("本日の試合", "TODAY")
                          + f'<div class="match-list">{cards}</div>')

        # ② 次の試合（本日分を除く今後のキックオフ最大10件）をスライダーで
        future = [m for m in matches
                  if m.get("kickoff_utc") and parse_iso(m["kickoff_utc"]) > now
                  and to_jst(m["kickoff_utc"]).date() != now_jst_date]
        future.sort(key=lambda m: m["kickoff_utc"])
        slider = match_slider(future[:10], tbn)
        if slider:
            upcoming_html = section_head("次の試合", "UP NEXT") + slider

    # ③ 直近行われた試合のハイライト（消化済みでハイライトがあるもの）
    recent_all = sorted(played, key=lambda m: m.get("date", ""), reverse=True)
    featured = highlight_strip(recent_all, tbn, highlights, limit=4)

    # ④ 最新ニュース10件
    news_items = (news or {}).get("items", [])
    news_html = ""
    if news_items:
        news_html = (section_head("最新ニュース", "NEWS")
                     + f'{news_list(news_items, limit=10)}'
                     '<p class="page-lead" style="margin-top:14px;">'
                     '<a class="news-more" href="news.html">ニュース一覧を見る ›</a></p>')

    body = (
        f'{hero_section()}'
        f'{today_html}{upcoming_html}{featured}{news_html}'
    )
    return body


def build_groups(structure, rankings, highlights=None):
    """グループステージ: タブでグループ切替。選択したグループの順位表＋試合カードを表示。"""
    from wc.render import group_standings, flag
    tbn = _teams_by_name(structure)
    standings = rankings.get("standings", {})
    matches = structure.get("matches", [])
    groups = structure.get("groups", [])

    # 日本の所属グループを先頭に（残りはA〜Lの自然順）
    jp_group = next((g["name"] for g in groups if "Japan" in g.get("teams", [])), None)
    ordered = ([g for g in groups if g["name"] == jp_group]
               + [g for g in groups if g["name"] != jp_group])

    tabs, panels = [], []
    for i, g in enumerate(ordered):
        gname = g["name"]
        letter = gname.replace("Group ", "")
        active = "is-active" if i == 0 else ""
        is_jp = gname == jp_group
        mark = flag("🇯🇵") if is_jp else ""
        tabs.append(
            f'<button class="grp-tab {active}" data-group="{gname}">{mark}{letter}</button>'
        )
        rows = standings.get(gname, [])
        table = group_standings(rows, tbn) if rows else \
            '<p class="page-lead">順位データはまだありません。</p>'
        g_matches = sorted(
            [m for m in matches if m.get("stage") == "group" and m.get("group") == gname],
            key=lambda m: (m.get("date", ""), m.get("kickoff_utc") or ""),
        )
        cards = "".join(match_card(m, tbn) for m in g_matches)
        match_html = (f'<div class="kick section-kicker grp-fx-label">日程・結果</div>'
                      f'<div class="match-list group-matches">{cards}</div>') if cards else ""
        hidden = "" if i == 0 else " hidden"
        panels.append(
            f'<div class="grp-panel" data-group="{gname}"{hidden}>{table}{match_html}</div>'
        )

    script = (
        '<script>document.querySelectorAll(".grp-tab").forEach(function(t){'
        't.addEventListener("click",function(){var g=t.dataset.group;'
        'document.querySelectorAll(".grp-tab").forEach(function(x){x.classList.toggle("is-active",x===t)});'
        'document.querySelectorAll(".grp-panel").forEach(function(p){p.hidden=p.dataset.group!==g});'
        '});});</script>'
    )

    body = (
        '<h1 class="page-title">グループリーグ順位表</h1>'
        '<p class="page-lead">タブでグループを切り替えて、各グループの順位と日程・結果をチェック。</p>'
        f'<div class="grp-tabs">{"".join(tabs)}</div>'
        f'<div class="grp-panels">{"".join(panels)}</div>'
        '<p class="grp-note">※ 各組上位2チームと、3位のうち成績上位8チームが決勝トーナメント出場権を獲得。</p>'
        f'{script}'
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
        '<p class="page-lead">「ワールドカップ2026」関連の最新ニュース（日本語）。</p>'
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
                       lineups, odds, gen, out):
    """各試合の個別ページを site/matches/{num}.html に生成。生成数を返す。"""
    tbn = _teams_by_name(structure)
    by_num = _resolved_matches_by_num(structure)
    mdir = out / "matches"
    mdir.mkdir(parents=True, exist_ok=True)
    for num, m in by_num.items():
        hl = highlights.get(match_key(m))
        md = lineups.get(match_key(m))
        od = odds.get(match_key(m))
        n1, n2 = jp_team(m.get("team1", "")), jp_team(m.get("team2", ""))
        title = f"{n1} vs {n2}"
        desc = f"ワールドカップ2026 {title} の日程・結果・スタメン・スタッツ・ハイライト動画・関連ニュース・日本での配信(DAZN/ABEMA/NHK ONE)。"
        body = match_detail(m, tbn, hl, news_items=news_items, squads_by_name=squads_by_name,
                            goals_by_name=goals_by_name, match_data=md, odds=od, gen=gen, base="../")
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
    odds = (read_json_or_none(data / "odds.json") or {}).get("items", {})
    goals_by_name = {s["name"]: s["goals"] for s in rankings.get("scorers", [])}
    gen = structure.get("generated_at", rankings.get("generated_at", ""))

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    pages = {
        "index.html": ("トップ", "index", build_index(structure, rankings, highlights, news),
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
                                   squads, goals_by_name, lineups, odds, gen, out)

    # assets/style.css をコピー
    assets = out / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for asset_name in ("style.css", "favicon.svg", "hero.png"):
        src = Path(templates_dir) / asset_name
        if src.exists():
            shutil.copyfile(src, assets / asset_name)

    print(f"サイト生成完了: {out}/ に {len(pages)} ページ + 試合 {n_matches} ページ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
