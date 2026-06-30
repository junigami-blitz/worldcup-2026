"""data/*.json を日テレ風v2デザインのHTMLフラグメント／ページへ変換する純粋関数群。

すべて入力dict→HTML文字列。ファイルI/Oは持たない（build_site が担当）。
動的テキストは html.escape でエスケープする。
"""
import html

from wc.i18n import jp_team, jp_round

# ナビゲーションタブ定義（キー, 表示名, リンク先）
_TABS = [
    ("index", "トップ", "index.html"),
    ("groups", "グループ", "groups.html"),
    ("knockout", "決勝トーナメント", "knockout.html"),
    ("rankings", "ランキング", "rankings.html"),
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
        name = _esc(g.get("name", ""))
        mark = _goal_marks(g)
        parts.append(
            f'<span class="goal"><span class="num gmin">{minute}\'</span> {name}{mark}</span>'
        )
    if not parts:
        return ""
    return '<span class="goals">' + " ・ ".join(parts) + "</span>"


def match_card(match, teams_by_name):
    """1試合のカードHTML。未消化試合はスコアの代わりに "vs"。"""
    t1, t2 = match["team1"], match["team2"]
    name1, name2 = _esc(jp_team(t1)), _esc(jp_team(t2))
    f1, f2 = _flag_of(t1, teams_by_name), _flag_of(t2, teams_by_name)

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
        meta = goal_line(match.get("goals1"), match.get("goals2"))
    else:
        win1 = win2 = ""
        score_html = '<div class="match-score match-score--vs">vs</div>'
        when = _esc(match.get("date", ""))
        meta = f'<span class="kickoff num">{when}</span>' if when else ""

    meta_html = f'<div class="match-meta">{meta}</div>' if meta else ""
    return (
        '<article class="match">'
        '<div class="match-teams">'
        f'<div class="team team-home {win1}">{f1}<span class="team-name">{name1}</span></div>'
        f'{score_html}'
        f'<div class="team team-away {win2}"><span class="team-name">{name2}</span>{f2}</div>'
        '</div>'
        f'{meta_html}'
        '</article>'
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
            f'<td class="col-player">{_esc(s["name"])}</td>'
            f'<td class="col-club">{_esc(jp_team(s["team"]))}</td>'
            f'<td class="num goals-cell">{s["goals"]}</td>'
            f'<td class="num">{s.get("penalties", 0)}</td>'
            '</tr>'
        )
    return f'<table class="scorers">{head}<tbody>{"".join(body)}</tbody></table>'


def _nav(active):
    items = []
    for key, label, href in _TABS:
        cls = "is-active" if key == active else ""
        items.append(f'<a class="tab {cls}" href="{href}">{label}</a>')
    return f'<nav class="tabs">{"".join(items)}</nav>'


def page_shell(title, active_tab, body_html, generated_at):
    """共通ページシェル（DOCTYPE・head・ヘッダ・ナビ・本文・フッタ）。"""
    gen = _esc(generated_at)
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(title)} | FIFA World Cup 2026</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="assets/style.css">
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
<div class="wrap">{_nav(active_tab)}</div>
<main class="wrap main">
{body_html}
</main>
<footer class="site-footer">
  <div class="wrap">
    <p class="foot-note">データ: openfootball（パブリックドメイン）。本サイトは非公式の解説サイトです。</p>
    <p class="foot-note kick">Last updated: <span class="num">{gen}</span></p>
  </div>
</footer>
</body>
</html>"""
