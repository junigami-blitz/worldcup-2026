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
    """国旗絵文字をチップで包む。空なら空文字。"""
    if not emoji:
        return ""
    return f'<span class="flag">{_esc(emoji)}</span>'


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
    """得点者を縦リストで（得点者名は日本語化）。無ければ空。"""
    rows = []
    for goals, team in ((match.get("goals1"), match.get("team1")),
                        (match.get("goals2"), match.get("team2"))):
        for g in goals or []:
            minute = _esc(g.get("minute", ""))
            name = _esc(jp_player(g.get("name", "")))
            mark = _goal_marks(g)
            rows.append(
                f'<li><span class="num gmin">{minute}\'</span> {name}{mark} '
                f'<span class="goal-team">{_esc(jp_team(team))}</span></li>'
            )
    if not rows:
        return ""
    return f'<div class="md-goals"><div class="kick section-kicker">得点</div><ul>{"".join(rows)}</ul></div>'


def _highlight_embed(highlight):
    """ハイライトをサムネイル＋タイトルで表示（YouTube）。無ければ空。"""
    if not highlight or not highlight.get("url"):
        return ""
    vid = _esc(highlight.get("videoId", ""))
    title = _esc(highlight.get("title", "ハイライト"))
    ch = _esc(highlight.get("channelTitle", ""))
    url = _esc(highlight["url"])
    thumb = f"https://img.youtube.com/vi/{vid}/mqdefault.jpg" if vid else ""
    thumb_html = (f'<img class="md-hl-thumb" src="{thumb}" alt="" loading="lazy" '
                  f'width="320" height="180">') if thumb else ""
    return (
        '<div class="md-hl">'
        '<div class="kick section-kicker">ハイライト</div>'
        f'<a class="md-hl-card" href="{url}" target="_blank" rel="noopener">'
        f'{thumb_html}'
        '<div class="md-hl-meta">'
        f'<div class="md-hl-title">{title}</div>'
        f'<div class="md-hl-ch kick">▷ {ch} で見る</div>'
        '</div></a></div>'
    )


def match_detail(match, teams_by_name, highlight=None, base="../"):
    """1試合の詳細ページ本体。日程・会場・得点・ハイライト・配信を掲載。"""
    t1, t2 = match["team1"], match["team2"]
    name1, name2 = _esc(jp_team(t1)), _esc(jp_team(t2))
    f1, f2 = _flag_of(t1, teams_by_name), _flag_of(t2, teams_by_name)
    when = _esc(jst_full(match.get("kickoff_utc")) or jst_label(match.get("kickoff_utc"))
                or match.get("date", ""))
    venue = _esc(match.get("ground", ""))

    # ラウンド／グループのコンテキスト
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
    return (
        f'<a class="md-back kick" href="{back}">‹ 一覧へ戻る</a>'
        f'<div class="kick section-kicker md-ctx">{_esc(ctx)}</div>'
        '<div class="md-head">'
        f'<div class="md-team {c1}">{f1}<span class="md-name">{name1}</span></div>'
        f'{score_html}'
        f'<div class="md-team {c2}"><span class="md-name">{name2}</span>{f2}</div>'
        '</div>'
        f'<div class="md-meta">{meta_bits}</div>'
        f'{_goal_list_block(match)}'
        f'{_highlight_embed(highlight)}'
        '<div class="md-stream">'
        '<div class="kick section-kicker">日本での視聴（配信）</div>'
        f'{streaming_badges(linked=True)}'
        '</div>'
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


def _news_thumb(source_url):
    """配信元ドメインのfaviconをサムネイルとして返す（記事画像はRSSに無いため）。"""
    if not source_url:
        return '<span class="news-thumb news-thumb--blank"></span>'
    from urllib.parse import urlparse
    domain = urlparse(source_url).netloc or source_url
    src = f"https://www.google.com/s2/favicons?domain={_esc(domain)}&sz=64"
    return (f'<img class="news-thumb" src="{src}" alt="" loading="lazy" '
            f'width="40" height="40">')


def news_list(items, limit=20):
    """ニュース記事リストのHTML（配信元favicon付き）。0件なら案内メッセージ。"""
    if not items:
        return '<p class="page-lead">表示できるニュースはありません。</p>'
    rows = []
    for it in items[:limit]:
        title = _esc(it.get("title", ""))
        link = _esc(it.get("link", ""))
        source = _esc(it.get("source", ""))
        pub = _esc(it.get("published", ""))
        thumb = _news_thumb(it.get("source_url", ""))
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


def highlight_strip(matches, teams_by_name, highlights, limit=4):
    """ハイライトのある直近の試合を「注目のハイライト」として並べる。無ければ空。"""
    if not highlights:
        return ""
    items = []
    for m in matches:
        if not (m.get("played") and m.get("score")):
            continue
        h = highlights.get(match_key(m))
        if not h or not h.get("url"):
            continue
        name1, name2 = _esc(jp_team(m["team1"])), _esc(jp_team(m["team2"]))
        f1, f2 = _flag_of(m["team1"], teams_by_name), _flag_of(m["team2"], teams_by_name)
        a, b = m["score"]["ft"][0], m["score"]["ft"][1]
        url = _esc(h["url"])
        items.append(
            f'<a class="hl-card" href="{url}" target="_blank" rel="noopener">'
            f'<span class="hl-teams">{f1}{name1} '
            f'<span class="num hl-score">{a}–{b}</span> {name2}{f2}</span>'
            '<span class="hl-cta kick">▷ ハイライト</span>'
            '</a>'
        )
        if len(items) >= limit:
            break
    if not items:
        return ""
    return (
        '<div class="kick section-kicker">注目のハイライト</div>'
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
