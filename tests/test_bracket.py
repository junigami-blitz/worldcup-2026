from wc.bracket import winner_of, loser_of, resolve_bracket


def _m(num, t1, t2, ft=None):
    return {"num": num, "team1": t1, "team2": t2,
            "played": ft is not None, "score": {"ft": ft} if ft else None}


def test_winner_and_loser():
    m = _m(73, "South Africa", "Canada", [0, 1])
    assert winner_of(m) == "Canada"
    assert loser_of(m) == "South Africa"


def test_winner_none_when_unplayed_or_draw():
    assert winner_of(_m(1, "A", "B")) is None
    assert winner_of(_m(1, "A", "B", [1, 1])) is None


def test_resolve_replaces_w_refs_with_winners():
    matches = [
        _m(73, "South Africa", "Canada", [0, 1]),   # Canada 勝
        _m(75, "Netherlands", "Morocco", [2, 1]),    # Netherlands 勝
        _m(90, "Canada", "W75"),                     # R16: Canada vs 75の勝者
    ]
    by_num = resolve_bracket(matches)
    assert by_num[90]["team1"] == "Canada"
    assert by_num[90]["team2"] == "Netherlands"  # W75 → Netherlands に解決


def test_resolve_keeps_placeholder_when_unresolved():
    matches = [
        _m(74, "Germany", "Paraguay"),   # 未消化
        _m(89, "W74", "W77"),            # 74が未消化なので解決不可
    ]
    by_num = resolve_bracket(matches)
    assert by_num[89]["team1"] == "W74"  # プレースホルダ維持


def test_resolve_handles_loser_ref_for_third_place():
    matches = [
        _m(101, "Spain", "Brazil", [0, 2]),   # Brazil 勝, Spain 敗
        _m(102, "France", "Argentina", [1, 0]),  # France 勝, Argentina 敗
        _m(103, "L101", "L102"),                 # 3位決定戦: 敗者同士
    ]
    by_num = resolve_bracket(matches)
    assert by_num[103]["team1"] == "Spain"
    assert by_num[103]["team2"] == "Argentina"


def test_resolve_multi_level():
    # R32 -> R16 -> QF まで連鎖解決
    matches = [
        _m(73, "A", "B", [1, 0]),  # A
        _m(75, "C", "D", [0, 1]),  # D
        _m(90, "A", "W75", [2, 0]),  # 90: A vs D -> A 勝（W75=D に解決後）
        _m(97, "W90", "X"),          # QF: W90 -> A
    ]
    by_num = resolve_bracket(matches)
    assert by_num[90]["team2"] == "D"
    assert by_num[97]["team1"] == "A"
