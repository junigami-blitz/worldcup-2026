"""決勝トーナメントのツリー解決。

openfootball の team1/team2 は "W74"（74番の勝者）や "L101"（101番の敗者）の
参照を含む。試合番号(num)の昇順に解決すると、各試合は自分より小さい番号しか
参照しないため一巡で実チーム名に展開できる。
"""
import re

_REF = re.compile(r"^([WL])(\d+)$")


def winner_of(match):
    """消化済みなら勝者チーム名。未消化・引分は None。"""
    if not (match and match.get("played") and match.get("score")):
        return None
    a, b = match["score"]["ft"][0], match["score"]["ft"][1]
    if a > b:
        return match["team1"]
    if b > a:
        return match["team2"]
    return None


def loser_of(match):
    """消化済みなら敗者チーム名。未消化・引分は None。"""
    if not (match and match.get("played") and match.get("score")):
        return None
    a, b = match["score"]["ft"][0], match["score"]["ft"][1]
    if a > b:
        return match["team2"]
    if b > a:
        return match["team1"]
    return None


def _resolve_ref(ref, by_num):
    """"W74"/"L101" を実チーム名へ。実チーム名はそのまま。解決不能なら参照のまま。"""
    if not ref:
        return ref
    m = _REF.match(ref)
    if not m:
        return ref  # すでに実チーム名
    n = int(m.group(2))
    target = by_num.get(n)
    name = winner_of(target) if m.group(1) == "W" else loser_of(target)
    return name or ref  # 未解決ならプレースホルダを維持


def resolve_bracket(matches):
    """num→試合dict（team1/team2を解決済み）を返す。元のdictは破壊しない。"""
    by_num = {m["num"]: dict(m) for m in matches if m.get("num") is not None}
    for num in sorted(by_num):
        m = by_num[num]
        m["team1"] = _resolve_ref(m.get("team1", ""), by_num)
        m["team2"] = _resolve_ref(m.get("team2", ""), by_num)
    return by_num
