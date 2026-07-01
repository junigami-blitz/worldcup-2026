"""data/*.json を日テレ風v2デザインのHTMLフラグメント／ページへ変換する純粋関数群。

すべて入力dict→HTML文字列。ファイルI/Oは持たない（build_site が担当）。
動的テキストは html.escape でエスケープする。
"""
import html
import re

from wc.i18n import jp_team, jp_round, jp_player
from wc.matchid import match_key
from wc.timeutil import jst_label, jst_full
from wc.streaming import streaming_for
from wc.flags import iso_from_emoji, flag_img_url
from wc.squads import age_on

# 公開サイトのベースURL（canonical / OGP 用）
SITE_URL = "https://junigami-blitz.github.io/worldcup-2026"
SITE_NAME = "ワールドカップ2026 速報・順位"
DEFAULT_DESCRIPTION = (
    "FIFAワールドカップ2026（カナダ・メキシコ・USA共催）の試合結果・順位表・"
    "得点王・ニュース・ハイライトを日本語で自動更新。"
)

# ナビゲーションタブ定義（キー, 表示名, リンク先）
_TABS = [
    ("index", "トップ", "index.html"),
    ("groups", "グループ", "groups.html"),
    ("knockout", "決勝トーナメント", "knockout.html"),
    ("rankings", "ランキング", "rankings.html"),
    ("news", "ニュース", "news.html"),
]


def _esc(s):
    return html.escape(str(s if s is not None else ""))


def flag(emoji):
    """国旗絵文字から flagcdn の国旗画像(img)を返す。導出不能/空なら空文字。"""
    iso = iso_from_emoji(emoji)
    url = flag_img_url(iso)
    if not url:
        return ""
    return f'<img class="flag" src="{_esc(url)}" alt="" loading="lazy">'


def _flag_of(team_name, teams_by_name):
    t = teams_by_name.get(team_name) or {}
    return flag(t.get("flag_icon", ""))


def _goal_marks(g):
    """PK/オウンゴールの注記を返す。"""
    if g.get("owngoal"):
        return "<span class=\"gmark\">OG</span>"
    if g.get("penalty"):
        return "<span class=\"gmark\">PK</span>"
    return ""


def goal_line(goals1, goals2):
    """両チームの得点者を "41' 久保 ・ 78' Pedri PK" 形式の1行HTMLにする。

    得点者がいなければ空文字。
    """
    parts = []
    for g in list(goals1 or []) + list(goals2 or []):
        minute = _esc(g.get("minute", ""))
        name = _esc(jp_player(g.get("name", "")))
        mark = _goal_marks(g)
        parts.append(
            f'<span class="goal"><span class="num gmin">{minute}\'</span> {name}{mark}</span>'
        )
    if not parts:
        return ""
    return '<span class="goals">' + " ・ ".join(parts) + "</span>"


def _highlight_link(match, highlights):
    """ハイライトがあれば控えめなテキストリンクを返す（無ければ空）。"""
    if not highlights:
        return ""
    h = highlights.get(match_key(match))
    if not h or not h.get("url"):
        return ""
    url = _esc(h["url"])
    return (
        f'<a class="match-highlight" href="{url}" target="_blank" rel="noopener">'
        '▷ ハイライト</a>'
    )


def match_href(match, base=""):
    """試合詳細ページへの相対URL。num が無ければ "#"。"""
    num = match.get("num")
    return f"{base}matches/{num}.html" if num is not None else "#"


def streaming_badges(services=None, linked=False):
    """配信サービスのバッジ列。linked=True で外部リンク、Falseはラベルのみ。"""
    services = services if services is not None else streaming_for()
    out = ['<span class="stream-label kick">配信</span>']
    for s in services:
        name = _esc(s["name"])
        if linked:
            out.append(
                f'<a class="stream-badge" href="{_esc(s["url"])}" '
                f'target="_blank" rel="noopener">{name}</a>'
            )
        else:
            out.append(f'<span class="stream-badge">{name}</span>')
    return f'<div class="match-stream">{"".join(out)}</div>'


def match_card(match, teams_by_name, base=""):
    """1試合のカード（詳細ページへのリンク）。日程(JST)・得点者・配信を表示。"""
    t1, t2 = match["team1"], match["team2"]
    name1, name2 = _esc(jp_team(t1)), _esc(jp_team(t2))
    f1, f2 = _flag_of(t1, teams_by_name), _flag_of(t2, teams_by_name)
    when = _esc(jst_label(match.get("kickoff_utc")) or match.get("date", ""))

    if match.get("played") and match.get("score"):
        a, b = match["score"]["ft"][0], match["score"]["ft"][1]
        win1 = "is-win" if a > b else ""
        win2 = "is-win" if b > a else ""
        score_html = (
            f'<div class="match-score num">'
            f'<span class="{win1}">{a}</span>'
            f'<span class="dash">–</span>'
            f'<span class="{win2}">{b}</span></div>'
        )
        goals = goal_line(match.get("goals1"), match.get("goals2"))
    else:
        win1 = win2 = ""
        score_html = '<div class="match-score match-score--vs">vs</div>'
        goals = ""

    when_html = f'<span class="match-when num">{when}</span>' if when else ""
    goals_html = f'<div class="match-meta">{goals}</div>' if goals else ""
    return (
        f'<a class="match" href="{match_href(match, base)}">'
        f'<div class="match-info">{when_html}<span class="match-more kick">詳細 ›</span></div>'
        '<div class="match-teams">'
        f'<div class="team team-home {win1}">{f1}<span class="team-name">{name1}</span></div>'
        f'{score_html}'
        f'<div class="team team-away {win2}"><span class="team-name">{name2}</span>{f2}</div>'
        '</div>'
        f'{goals_html}'
        f'{streaming_badges()}'
        '</a>'
    )


def section_head(title_jp, title_en=""):
    """トップページ用の見出し（赤いアクセントバー＋和文＋英字サブラベル）。"""
    en = f'<span class="sec-en kick">{_esc(title_en)}</span>' if title_en else ""
    return (
        '<div class="sec-head">'
        '<span class="sec-bar"></span>'
        f'<span class="sec-jp">{_esc(title_jp)}</span>'
        f'{en}'
        '</div>'
    )


def slider_card(match, teams_by_name, base=""):
    """スライダー用の縦積みコンパクトカード。日時＋2チーム(国旗+国名)＋詳細。"""
    t1, t2 = match.get("team1", ""), match.get("team2", "")
    name1, name2 = _esc(jp_team(t1)), _esc(jp_team(t2))
    f1, f2 = _flag_of(t1, teams_by_name), _flag_of(t2, teams_by_name)
    when = _esc(jst_label(match.get("kickoff_utc")) or match.get("date", ""))

    if match.get("played") and match.get("score"):
        a, b = match["score"]["ft"][0], match["score"]["ft"][1]
        mid = (f'<div class="msc-score num">'
               f'<span class="{"is-win" if a > b else ""}">{a}</span>'
               f'<span class="dash">–</span>'
               f'<span class="{"is-win" if b > a else ""}">{b}</span></div>')
    else:
        mid = '<div class="msc-vs kick">VS</div>'

    return (
        f'<a class="ms-card" href="{match_href(match, base)}">'
        f'<div class="msc-when num">{when}</div>'
        '<div class="msc-body">'
        f'<div class="msc-team"><span class="msc-flag">{f1}</span>'
        f'<span class="msc-name">{name1}</span></div>'
        f'{mid}'
        f'<div class="msc-team"><span class="msc-flag">{f2}</span>'
        f'<span class="msc-name">{name2}</span></div>'
        '</div>'
        '<div class="msc-more kick">詳細 ›</div>'
        '</a>'
    )


def match_slider(matches, teams_by_name, base=""):
    """試合カードを横スクロールのスライダーで並べる。矢印ボタンでスクロール。"""
    if not matches:
        return ""
    slides = "".join(
        f'<div class="ms-slide">{slider_card(m, teams_by_name, base)}</div>'
        for m in matches
    )
    return (
        '<div class="match-slider">'
        '<button class="ms-nav ms-prev" aria-label="前へ" '
        'onclick="this.parentNode.querySelector(\'.ms-track\').scrollBy({left:-260,behavior:\'smooth\'})">‹</button>'
        f'<div class="ms-track">{slides}</div>'
        '<button class="ms-nav ms-next" aria-label="次へ" '
        'onclick="this.parentNode.querySelector(\'.ms-track\').scrollBy({left:260,behavior:\'smooth\'})">›</button>'
        '</div>'
    )


_REF_RE = re.compile(r"^[WL]\d+$")


def _bk_team_row(team, score, is_win, teams_by_name):
    """ブラケット1チーム行（国旗＋名前＋スコア）。W74等の未確定は淡色表示。"""
    tbd = bool(_REF_RE.match(team or ""))
    name = _esc(team) if tbd else _esc(jp_team(team))
    fl = "" if tbd else _flag_of(team, teams_by_name)
    win_cls = " is-win" if is_win else ""
    tbd_cls = " is-tbd" if tbd else ""
    return (
        f'<div class="bk-team{win_cls}{tbd_cls}">'
        f'<span class="bk-flag">{fl}</span>'
        f'<span class="bk-name">{name}</span>'
        f'<span class="bk-score num">{score}</span>'
        '</div>'
    )


def bracket_node(match, teams_by_name, base=""):
    """ブラケットの1試合ボックス（日時＋2チーム行＋配信）。詳細ページへリンク。"""
    if not match:
        return '<div class="bk-node is-empty"></div>'
    t1, t2 = match.get("team1", ""), match.get("team2", "")
    played = match.get("played") and match.get("score")
    if played:
        a, b = match["score"]["ft"][0], match["score"]["ft"][1]
        s1, s2 = str(a), str(b)
        w1, w2 = a > b, b > a
    else:
        s1 = s2 = "–"
        w1 = w2 = False

    label = jst_label(match.get("kickoff_utc"))
    svc = " ".join(_esc(s["name"]) for s in streaming_for())
    return (
        f'<a class="bk-node" href="{match_href(match, base)}">'
        '<div class="bk-inner">'
        f'<div class="bk-when num">{_esc(label)}</div>'
        '<div class="bk-box">'
        f'{_bk_team_row(t1, s1, w1, teams_by_name)}'
        f'{_bk_team_row(t2, s2, w2, teams_by_name)}'
        '</div>'
        f'<div class="bk-stream">{svc}</div>'
        '</div>'
        '</a>'
    )


def _goal_list_block(match):
    """得点者を両国側（ホーム=左 / アウェイ=右）に振り分けて表示。中央に⚽。"""
    g1 = match.get("goals1") or []
    g2 = match.get("goals2") or []
    if not g1 and not g2:
        return ""

    def side(goals, home):
        out = []
        for g in goals:
            minute = _esc(g.get("minute", ""))
            name = _esc(jp_player(g.get("name", "")))
            mark = _goal_marks(g)
            if home:
                out.append(f'<div class="mg-goal">{name}{mark} '
                           f'<span class="num mg-min">{minute}\'</span></div>')
            else:
                out.append(f'<div class="mg-goal"><span class="num mg-min">{minute}\'</span> '
                           f'{name}{mark}</div>')
        return "".join(out)

    return (
        '<div class="md-goals"><div class="md-goals-grid">'
        f'<div class="mg-side mg-home">{side(g1, True)}</div>'
        '<div class="mg-icon">⚽</div>'
        f'<div class="mg-side mg-away">{side(g2, False)}</div>'
        '</div></div>'
    )


def videos_of(highlight):
    """ハイライトエントリから動画リストを返す（新旧フォーマット両対応）。"""
    if not highlight:
        return []
    if highlight.get("videos"):
        return highlight["videos"]
    if highlight.get("videoId") or highlight.get("url"):
        return [highlight]  # 旧フォーマット（単一）
    return []


def _highlight_embeds(highlight):
    """ハイライト動画を YouTube 埋め込み(iframe)で複数表示。無ければ空。"""
    videos = videos_of(highlight)
    cards = []
    for v in videos:
        vid = _esc(v.get("videoId", ""))
        if not vid:
            continue
        title = _esc(v.get("title", "ハイライト"))
        ch = _esc(v.get("channelTitle", ""))
        cards.append(
            '<div class="md-vid">'
            '<div class="md-vid-frame">'
            f'<iframe src="https://www.youtube-nocookie.com/embed/{vid}" title="{title}" '
            'loading="lazy" allowfullscreen '
            'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture">'
            '</iframe></div>'
            f'<div class="md-vid-title">{title}</div>'
            f'<div class="md-vid-ch kick">{ch}</div>'
            '</div>'
        )
    if not cards:
        return ""
    return (
        '<div class="md-hl">'
        '<div class="kick section-kicker">ハイライト動画</div>'
        f'<div class="md-vids">{"".join(cards)}</div>'
        '</div>'
    )


def related_news(match, news_items, limit=None):
    """タイトルに両チーム名（日本語/英語いずれか）を含むニュースを抽出。

    limit=None なら該当する限りすべて返す。
    """
    n1, n2 = jp_team(match.get("team1", "")), jp_team(match.get("team2", ""))
    e1, e2 = match.get("team1", ""), match.get("team2", "")
    out = []
    for it in news_items or []:
        title = it.get("title", "")
        has1 = (n1 and n1 in title) or (e1 and e1 in title)
        has2 = (n2 and n2 in title) or (e2 and e2 in title)
        if has1 and has2:
            out.append(it)
            if limit is not None and len(out) >= limit:
                break
    return out


_POS_ORDER = ["GK", "DF", "MF", "FW"]
_POS_JP = {"GK": "GK", "DF": "DF", "MF": "MF", "FW": "FW"}


def squad_block(team_label, flag_html, players, ref_iso, goals_by_name=None):
    """1チームの代表メンバーをポジション別に表示。"""
    if not players:
        return ""
    goals_by_name = goals_by_name or {}
    from collections import OrderedDict
    groups = OrderedDict((p, []) for p in _POS_ORDER)
    others = []
    for pl in players:
        if pl.get("pos") in groups:
            groups[pl["pos"]].append(pl)
        else:
            others.append(pl)
    sections = []
    for pos in _POS_ORDER:
        pls = groups[pos]
        if not pls:
            continue
        rows = []
        for pl in sorted(pls, key=lambda x: (x.get("number") or 99)):
            num = pl.get("number", "")
            name = _esc(jp_player(pl.get("name", "")))
            club = _esc(pl.get("club", ""))
            a = age_on(pl.get("dob", ""), ref_iso)
            age_str = f"{a}歳" if a is not None else ""
            g = goals_by_name.get(pl.get("name", ""), 0)
            goal_badge = f'<span class="sq-goal">⚽{g}</span>' if g else ""
            rows.append(
                '<li class="sq-row">'
                f'<span class="num sq-num">{_esc(num)}</span>'
                f'<span class="sq-name">{name}{goal_badge}</span>'
                f'<span class="sq-club">{club}</span>'
                f'<span class="sq-age num">{age_str}</span>'
                '</li>'
            )
        sections.append(
            f'<div class="sq-pos"><div class="kick sq-pos-label">{_POS_JP[pos]}</div>'
            f'<ul class="sq-list">{"".join(rows)}</ul></div>'
        )
    return (
        '<div class="md-squad-team">'
        f'<div class="md-squad-head">{flag_html}<span>{_esc(team_label)}</span></div>'
        f'{"".join(sections)}'
        '</div>'
    )


_AF_POS = {"G": "GK", "D": "DF", "M": "MF", "F": "FW"}
_STAT_JP = {
    "Ball Possession": "ボール支配率",
    "Total Shots": "シュート",
    "Shots on Goal": "枠内シュート",
    "Shots off Goal": "枠外シュート",
    "Blocked Shots": "ブロック",
    "Shots insidebox": "ボックス内シュート",
    "Shots outsidebox": "ボックス外シュート",
    "Corner Kicks": "コーナーキック",
    "Offsides": "オフサイド",
    "Fouls": "ファウル",
    "Yellow Cards": "イエローカード",
    "Red Cards": "レッドカード",
    "Goalkeeper Saves": "GKセーブ",
    "Total passes": "総パス",
    "Passes accurate": "成功パス",
    "Passes %": "パス成功率",
    "expected_goals": "期待値(xG)",
}


def _lineup_team(lu, flag, name):
    """1チームのスタメン（フォーメーション＋ポジション別startXI＋控え）。"""
    formation = _esc(lu.get("formation", ""))
    from collections import OrderedDict
    groups = OrderedDict((p, []) for p in ("GK", "DF", "MF", "FW"))
    for pl in lu.get("startXI", []):
        pos = _AF_POS.get(pl.get("pos", ""), "FW")
        groups.setdefault(pos, []).append(pl)
    blocks = []
    for pos, pls in groups.items():
        if not pls:
            continue
        items = "".join(
            f'<li><span class="num sq-num">{_esc(p.get("number") or "")}</span>'
            f'<span class="sq-name">{_esc(jp_player(p.get("name", "")))}</span></li>'
            for p in pls
        )
        blocks.append(f'<div class="sq-pos"><div class="kick sq-pos-label">{pos}</div>'
                      f'<ul class="sq-list lu-list">{items}</ul></div>')
    subs = lu.get("substitutes", [])
    subs_html = ""
    if subs:
        names = " ・ ".join(f'{_esc(s.get("number") or "")} {_esc(jp_player(s.get("name", "")))}'
                            for s in subs)
        subs_html = f'<div class="lu-subs"><span class="kick lu-subs-label">控え</span> {names}</div>'
    return (
        '<div class="md-squad-team">'
        f'<div class="md-squad-head">{flag}<span>{_esc(name)}</span>'
        f'<span class="lu-formation num">{formation}</span></div>'
        f'{"".join(blocks)}{subs_html}'
        '</div>'
    )


def _team_stats_compare(team_stats, t1, t2):
    """2チームのチームスタッツを左右対比で表示。"""
    if not team_stats or len(team_stats) < 2:
        return ""
    by = {ts["team"]: {s["type"]: s["value"] for s in ts.get("stats", [])} for ts in team_stats}
    # team_stats のチーム名は API 表記。引数 t1/t2 は openfootball 表記なので順序は team_stats の並び順に従う
    a = team_stats[0].get("stats", [])
    name_a = team_stats[0].get("team", "")
    name_b = team_stats[1].get("team", "") if len(team_stats) > 1 else ""
    map_b = {s["type"]: s["value"] for s in team_stats[1].get("stats", [])}
    rows = []
    for s in a:
        typ = s["type"]
        label = _STAT_JP.get(typ, typ)
        va = s.get("value")
        vb = map_b.get(typ, "")
        rows.append(
            f'<div class="ts-row"><span class="ts-a num">{_esc(va)}</span>'
            f'<span class="ts-label">{_esc(label)}</span>'
            f'<span class="ts-b num">{_esc(vb)}</span></div>'
        )
    if not rows:
        return ""
    return (
        '<div class="md-tstats"><div class="kick section-kicker">チームスタッツ</div>'
        f'<div class="ts-head"><span>{_esc(name_a)}</span><span></span><span>{_esc(name_b)}</span></div>'
        f'{"".join(rows)}</div>'
    )


def _player_stats_block(players_data):
    """選手スタッツ（出場選手のみ）をチームごとの表で。"""
    blocks = []
    for team in players_data or []:
        rows = []
        for p in sorted(team.get("players", []),
                        key=lambda x: (-(float(x["rating"]) if x.get("rating") else 0))):
            if not p.get("minutes"):
                continue
            rating = _esc(p.get("rating") or "-")
            rows.append(
                '<tr>'
                f'<td class="ps-name">{_esc(jp_player(p.get("name", "")))}</td>'
                f'<td class="num">{_esc(p.get("minutes") or 0)}\'</td>'
                f'<td class="num ps-rating">{rating}</td>'
                f'<td class="num">{_esc(p.get("goals") or 0)}</td>'
                f'<td class="num">{_esc(p.get("shots") or 0)}</td>'
                f'<td class="num">{_esc(p.get("passes") or 0)}</td>'
                '</tr>'
            )
        if not rows:
            continue
        head = ('<thead><tr class="kick"><th class="ps-name">選手</th><th>分</th>'
                '<th>評価</th><th>得点</th><th>射</th><th>パス</th></tr></thead>')
        blocks.append(
            f'<div class="ps-team"><div class="kick block-kicker">{_esc(team.get("team", ""))}</div>'
            f'<table class="scorers ps-table">{head}<tbody>{"".join(rows)}</tbody></table></div>'
        )
    if not blocks:
        return ""
    return ('<div class="md-pstats"><div class="kick section-kicker">選手スタッツ</div>'
            f'<div class="ps-grid">{"".join(blocks)}</div></div>')


def _lineup_section(match_data, teams_by_name, t1, t2):
    """スタメン＋チームスタッツ＋選手スタッツをまとめて返す。データ無しは空。"""
    if not match_data:
        return ""
    lineups = match_data.get("lineups") or []
    parts = []
    if len(lineups) >= 2:
        f1 = _flag_of(t1, teams_by_name)
        f2 = _flag_of(t2, teams_by_name)
        # lineups の並びに合わせてチーム名（API表記）で表示
        b1 = _lineup_team(lineups[0], f1, jp_team(t1))
        b2 = _lineup_team(lineups[1], f2, jp_team(t2))
        parts.append(
            '<div class="md-squad"><div class="kick section-kicker">スターティングメンバー</div>'
            f'<div class="md-squad-grid">{b1}{b2}</div></div>'
        )
    parts.append(_team_stats_compare(match_data.get("team_stats"), t1, t2))
    parts.append(_player_stats_block(match_data.get("players")))
    return "".join(p for p in parts if p)


def odds_block(odds, name1, name2):
    """ブックメーカーのオッズと勝率換算を「勝敗予想の材料」として表示。免責付き。"""
    if not odds:
        return ""
    probs = odds.get("probs") or {}
    od = odds.get("odds") or {}
    books = odds.get("books", 0)
    ph, pd, pa = probs.get("home", 0), probs.get("draw", 0), probs.get("away", 0)
    oh, odw, oa = od.get("home"), od.get("draw"), od.get("away")

    def bar(label, pct, odd, cls):
        odd_s = f'{odd:.2f}' if isinstance(odd, (int, float)) else "-"
        return (
            f'<div class="od-row">'
            f'<span class="od-name">{label}</span>'
            f'<span class="od-barwrap"><span class="od-bar {cls}" style="width:{pct}%"></span></span>'
            f'<span class="od-pct num">{pct}%</span>'
            f'<span class="od-odd num">{odd_s}</span>'
            '</div>'
        )
    rows = (bar(_esc(name1), ph, oh, "od-home")
            + bar("引き分け", pd, odw, "od-draw")
            + bar(_esc(name2), pa, oa, "od-away"))
    captured = jst_full(odds.get("captured", "")) if odds.get("captured") else ""
    when = f'（{_esc(captured)} 時点）' if captured else ""
    note = ("※ 海外ブックメーカーの平均オッズに基づく参考値（勝率は控除率調整後）で、"
            "キックオフ直前の最終取得時点のものです。勝敗予想の目安であり、賭博の推奨・"
            "斡旋を目的とするものではありません。20歳未満の賭博は法律で禁止されています。")
    return (
        '<div class="md-odds">'
        '<div class="kick section-kicker">勝敗予想（ブックメーカー・オッズ）</div>'
        f'<div class="od-table" data-books="{books}">'
        '<div class="od-head kick"><span>結果</span><span>勝率換算</span><span>オッズ</span></div>'
        f'{rows}</div>'
        f'<p class="od-books kick">{books} 社のオッズ平均{when}</p>'
        f'<p class="md-note od-note">{note}</p>'
        '</div>'
    )


def match_detail(match, teams_by_name, highlight=None, news_items=None,
                 squads_by_name=None, goals_by_name=None, match_data=None,
                 odds=None, gen="", base="../"):
    """1試合の詳細ページ本体。日程・得点・ハイライト動画・関連ニュース・スカッド・配信。"""
    t1, t2 = match["team1"], match["team2"]
    name1, name2 = _esc(jp_team(t1)), _esc(jp_team(t2))
    f1, f2 = _flag_of(t1, teams_by_name), _flag_of(t2, teams_by_name)
    when = _esc(jst_full(match.get("kickoff_utc")) or jst_label(match.get("kickoff_utc"))
                or match.get("date", ""))
    venue = _esc(match.get("ground", ""))

    rnd = jp_round(match.get("round", ""))
    grp = match.get("group")
    ctx = f'{_esc((grp or "").replace("Group ", "グループ"))} {rnd}'.strip() if grp else rnd
    back = f'{base}knockout.html' if match.get("stage") == "knockout" else f'{base}groups.html'

    if match.get("played") and match.get("score"):
        a, b = match["score"]["ft"][0], match["score"]["ft"][1]
        c1 = "is-win" if a > b else ""
        c2 = "is-win" if b > a else ""
        score_html = (f'<div class="md-score num"><span class="{c1}">{a}</span>'
                      f'<span class="dash">–</span><span class="{c2}">{b}</span></div>')
    else:
        c1 = c2 = ""
        score_html = '<div class="md-score md-score--vs">vs</div>'

    meta_bits = " · ".join(x for x in [f'<span class="num">{when}</span>' if when else "",
                                       venue] if x)

    # 関連ニュース
    news_html = ""
    rel = related_news(match, news_items)  # 該当する限りすべて
    if rel:
        news_html = ('<div class="md-news">'
                     f'<div class="kick section-kicker">関連ニュース（{len(rel)}件）</div>'
                     f'{news_list(rel, limit=len(rel))}</div>')

    # スタメン＋スタッツ（API-Footballデータがあれば）。無ければ代表メンバー。
    lineup_html = _lineup_section(match_data, teams_by_name, t1, t2)
    squad_html = ""
    if not lineup_html:
        sbn = squads_by_name or {}
        p1, p2 = sbn.get(t1), sbn.get(t2)
        if p1 or p2:
            b1 = squad_block(name1, f1, p1 or [], gen, goals_by_name)
            b2 = squad_block(name2, f2, p2 or [], gen, goals_by_name)
            squad_html = (
                '<div class="md-squad">'
                '<div class="kick section-kicker">代表メンバー（スカッド）</div>'
                '<p class="md-note">※ スタメン情報が取得でき次第そちらを表示します。現在は各国の登録メンバーです。</p>'
                f'<div class="md-squad-grid">{b1}{b2}</div>'
                '</div>'
            )

    return (
        f'<a class="md-back kick" href="{back}">‹ 一覧へ戻る</a>'
        f'<div class="kick section-kicker md-ctx">{_esc(ctx)}</div>'
        '<div class="md-head">'
        f'<div class="md-team {c1}">{f1}<span class="md-name">{name1}</span></div>'
        f'{score_html}'
        f'<div class="md-team {c2}"><span class="md-name">{name2}</span>{f2}</div>'
        '</div>'
        f'<div class="md-meta">{meta_bits}</div>'
        f'{odds_block(odds, name1, name2)}'
        f'{_goal_list_block(match)}'
        f'{_highlight_embeds(highlight)}'
        f'{news_html}'
        '<div class="md-stream">'
        '<div class="kick section-kicker">日本での視聴（配信）</div>'
        f'{streaming_badges(linked=True)}'
        '</div>'
        f'{lineup_html}'
        f'{squad_html}'
    )


def standings_table(group_label, rows, teams_by_name):
    """グループ順位表HTML。上位2チームに突破ライン(is-advance)、3位に is-playoff。"""
    head = (
        '<thead><tr class="kick">'
        '<th class="col-team">チーム</th>'
        '<th>試</th><th>勝</th><th>分</th><th>敗</th>'
        '<th>得</th><th>失</th><th>差</th><th class="col-pts">点</th>'
        '</tr></thead>'
    )
    body = []
    for r in rows:
        pos = r["pos"]
        cls = "is-advance" if pos <= 2 else ("is-playoff" if pos == 3 else "")
        name = _esc(jp_team(r["team"]))
        fl = _flag_of(r["team"], teams_by_name)
        gd = r["gd"]
        gd_str = f"+{gd}" if gd > 0 else (str(gd) if gd != 0 else "0")
        body.append(
            f'<tr class="{cls}">'
            f'<td class="col-team"><span class="num pos">{pos}</span>{fl}{name}</td>'
            f'<td class="num">{r["played"]}</td>'
            f'<td class="num">{r["win"]}</td>'
            f'<td class="num">{r["draw"]}</td>'
            f'<td class="num">{r["loss"]}</td>'
            f'<td class="num">{r["gf"]}</td>'
            f'<td class="num">{r["ga"]}</td>'
            f'<td class="num">{gd_str}</td>'
            f'<td class="num col-pts">{r["points"]}</td>'
            '</tr>'
        )
    return (
        f'<div class="standings-block">'
        f'<div class="kick block-kicker">{_esc(group_label)}</div>'
        f'<table class="standings">{head}<tbody>{"".join(body)}</tbody></table>'
        '</div>'
    )


def group_standings(rows, teams_by_name):
    """タブUI用のグループ順位表（ダークヘッダ・勝/分/敗/Pt/得/失、突破ハイライト）。"""
    head = (
        '<thead><tr class="gs-head">'
        '<th class="gs-team">国</th><th>勝</th><th>分</th><th>敗</th>'
        '<th class="gs-pt">Pt</th><th>得</th><th>失</th>'
        '</tr></thead>'
    )
    body = []
    for r in rows:
        pos = r["pos"]
        cls = "is-q" if pos <= 2 else ("is-po" if pos == 3 else "is-out")
        name = _esc(jp_team(r["team"]))
        fl = _flag_of(r["team"], teams_by_name)
        body.append(
            f'<tr class="{cls}">'
            f'<td class="gs-team"><span class="num gs-pos">{pos}</span>{fl}'
            f'<span class="gs-name">{name}</span></td>'
            f'<td class="num">{r["win"]}</td>'
            f'<td class="num">{r["draw"]}</td>'
            f'<td class="num">{r["loss"]}</td>'
            f'<td class="num gs-pt">{r["points"]}</td>'
            f'<td class="num">{r["gf"]}</td>'
            f'<td class="num">{r["ga"]}</td>'
            '</tr>'
        )
    return f'<table class="gs-table">{head}<tbody>{"".join(body)}</tbody></table>'


def scorers_table(scorers, top_n=20):
    """得点王ランキング表HTML（top_n 件まで）。"""
    head = (
        '<thead><tr class="kick">'
        '<th class="col-rank">#</th><th class="col-player">選手</th>'
        '<th class="col-club">代表</th><th>得点</th><th>PK</th>'
        '</tr></thead>'
    )
    body = []
    for i, s in enumerate(scorers[:top_n], start=1):
        body.append(
            '<tr>'
            f'<td class="num col-rank">{i}</td>'
            f'<td class="col-player">{_esc(jp_player(s["name"]))}</td>'
            f'<td class="col-club">{_esc(jp_team(s["team"]))}</td>'
            f'<td class="num goals-cell">{s["goals"]}</td>'
            f'<td class="num">{s.get("penalties", 0)}</td>'
            '</tr>'
        )
    return f'<table class="scorers">{head}<tbody>{"".join(body)}</tbody></table>'


def _news_thumb(item):
    """サムネイル。全記事で同じ枠サイズ(news-thumb)に統一する。

    アイキャッチ画像があれば枠いっぱいに写真、無ければ配信元faviconを枠の中央に、
    それも無ければ空の枠。画像あり/なしが混在してもグリッドが揃う。
    """
    image = (item.get("image") or "").strip()
    if image:
        return (f'<img class="news-thumb news-thumb--eyecatch" src="{_esc(image)}" '
                f'alt="" loading="lazy">')
    source_url = item.get("source_url", "")
    if not source_url:
        return '<span class="news-thumb news-thumb--blank"></span>'
    from urllib.parse import urlparse
    domain = urlparse(source_url).netloc or source_url
    src = f"https://www.google.com/s2/favicons?domain={_esc(domain)}&sz=64"
    return (f'<span class="news-thumb news-thumb--logo">'
            f'<img class="news-favicon" src="{src}" alt="" loading="lazy"></span>')


def news_list(items, limit=20):
    """ニュース記事リストのHTML（アイキャッチ画像付き）。0件なら案内メッセージ。"""
    if not items:
        return '<p class="page-lead">表示できるニュースはありません。</p>'
    rows = []
    for it in items[:limit]:
        title = _esc(it.get("title", ""))
        link = _esc(it.get("link", ""))
        source = _esc(it.get("source", ""))
        pub = _esc(it.get("published", ""))
        thumb = _news_thumb(it)
        meta = " · ".join(x for x in [source, f'<span class="num">{pub}</span>' if pub else ""] if x)
        rows.append(
            '<article class="news-item">'
            f'<a class="news-link" href="{link}" target="_blank" rel="noopener">'
            f'{thumb}'
            '<span class="news-body">'
            f'<span class="news-title">{title}</span>'
            f'<span class="news-meta kick">{meta}</span>'
            '</span></a>'
            '</article>'
        )
    return f'<div class="news-list">{"".join(rows)}</div>'


def team_stats_table(rows, teams_by_name, top_n=20):
    """チーム得点/失点ランキング表HTML（総得点降順、top_n件）。"""
    head = (
        '<thead><tr class="kick">'
        '<th class="col-rank">#</th><th class="col-team">チーム</th>'
        '<th>試</th><th>得点</th><th>失点</th><th>差</th>'
        '</tr></thead>'
    )
    body = []
    for i, r in enumerate(rows[:top_n], start=1):
        name = _esc(jp_team(r["team"]))
        fl = _flag_of(r["team"], teams_by_name)
        gd = r["gd"]
        gd_str = f"+{gd}" if gd > 0 else (str(gd) if gd != 0 else "0")
        body.append(
            '<tr>'
            f'<td class="num col-rank">{i}</td>'
            f'<td class="col-team">{fl}{name}</td>'
            f'<td class="num">{r["played"]}</td>'
            f'<td class="num goals-cell">{r["gf"]}</td>'
            f'<td class="num">{r["ga"]}</td>'
            f'<td class="num">{gd_str}</td>'
            '</tr>'
        )
    return f'<table class="scorers team-stats">{head}<tbody>{"".join(body)}</tbody></table>'


def highlight_strip(matches, teams_by_name, highlights, limit=4, base=""):
    """ハイライトのある直近試合を「注目のハイライト」として並べ、試合詳細へリンク。"""
    if not highlights:
        return ""
    items = []
    for m in matches:
        if not (m.get("played") and m.get("score")):
            continue
        vids = videos_of(highlights.get(match_key(m)))
        if not vids:
            continue
        vid = _esc(vids[0].get("videoId", ""))
        thumb = (f'<img class="hl-thumb" src="https://img.youtube.com/vi/{vid}/mqdefault.jpg" '
                 f'alt="" loading="lazy">') if vid else ""
        name1, name2 = _esc(jp_team(m["team1"])), _esc(jp_team(m["team2"]))
        f1, f2 = _flag_of(m["team1"], teams_by_name), _flag_of(m["team2"], teams_by_name)
        a, b = m["score"]["ft"][0], m["score"]["ft"][1]
        items.append(
            f'<a class="hl-card" href="{match_href(m, base)}">'
            f'{thumb}'
            '<span class="hl-info">'
            f'<span class="hl-teams">{f1}{name1} '
            f'<span class="num hl-score">{a}–{b}</span> {name2}{f2}</span>'
            f'<span class="hl-cta kick">▷ ハイライト {len(vids)}本</span>'
            '</span></a>'
        )
        if len(items) >= limit:
            break
    if not items:
        return ""
    return (
        f'{section_head("注目のハイライト", "HIGHLIGHTS")}'
        f'<div class="hl-strip">{"".join(items)}</div>'
    )


def _nav(active, base=""):
    items = []
    for key, label, href in _TABS:
        cls = "is-active" if key == active else ""
        items.append(f'<a class="tab {cls}" href="{base}{href}">{label}</a>')
    return f'<nav class="tabs">{"".join(items)}</nav>'


def _jsonld_block():
    """大会全体の SportsEvent 構造化データ（JSON-LD）。"""
    import json
    data = {
        "@context": "https://schema.org",
        "@type": "SportsEvent",
        "name": "FIFA ワールドカップ 2026",
        "sport": "Soccer",
        "startDate": "2026-06-11",
        "endDate": "2026-07-19",
        "location": {"@type": "Place", "name": "カナダ・メキシコ・アメリカ合衆国"},
        "url": SITE_URL + "/",
    }
    return ('<script type="application/ld+json">'
            + json.dumps(data, ensure_ascii=False) + "</script>")


def page_shell(title, active_tab, body_html, generated_at,
               description=None, path="index.html", jsonld=False, base=""):
    """共通ページシェル（DOCTYPE・head・ヘッダ・ナビ・本文・フッタ）。

    description / path で SEO・OGP・canonical を出力。jsonld=True で構造化データ。
    base はサブディレクトリ用の相対プレフィックス（例: "../"）。
    """
    desc = _esc(description or DEFAULT_DESCRIPTION)
    full_title = f"{_esc(title)} | {_esc(SITE_NAME)}"
    canonical = f"{SITE_URL}/{path}"
    jsonld_html = _jsonld_block() if jsonld else ""
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{full_title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{_esc(SITE_NAME)}">
<meta property="og:title" content="{full_title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canonical}">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{full_title}">
<meta name="twitter:description" content="{desc}">
{jsonld_html}
<link rel="icon" href="{base}assets/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="{base}assets/style.css">
</head>
<body>
<header class="site-header">
  <div class="wrap header-inner">
    <div class="wordmark">
      <div class="kick wm-kicker">FIFA World Cup 2026</div>
      <div class="wm-title">ワールドカップ2026 速報・順位</div>
    </div>
    <div class="kick host">Canada · Mexico · USA</div>
  </div>
</header>
<div class="wrap">{_nav(active_tab, base)}</div>
<main class="wrap main">
{body_html}
</main>
<footer class="site-footer">
  <div class="wrap">
    <p class="foot-note">データ: openfootball（パブリックドメイン）。本サイトは非公式の解説サイトです。</p>
    <p class="foot-note kick">最終更新: <span class="num">{_esc(jst_full(generated_at) or generated_at)}</span></p>
  </div>
</footer>
</body>
</html>"""
