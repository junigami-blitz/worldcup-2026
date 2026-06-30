"""試合を一意に識別するキー。highlights のキャッシュ突き合わせに使う。"""


def match_key(match):
    """日付＋対戦カードから安定キーを生成（"YYYY-MM-DD|team1|team2"）。"""
    return f"{match.get('date', '')}|{match.get('team1', '')}|{match.get('team2', '')}"
