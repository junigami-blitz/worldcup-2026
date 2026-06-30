"""国旗絵文字 → ISOコード → flagcdn の国旗画像URL。

絵文字（flag_icon）から ISO 3166-1 alpha-2 コードを導出する：
- 通常国: 地域指示子記号ペア（🇯🇵 = U+1F1EF U+1F1F5 → "jp"）
- イングランド/スコットランド等: 🏴(U+1F3F4) + タグ文字列（"gbeng" → "gb-eng"）
手動マッピング不要で全48チームを変換できる。
"""

_RI_BASE = 0x1F1E6  # 🇦
_TAG_A = 0xE0061     # tag 'a'
_TAG_Z = 0xE007A     # tag 'z'
_BLACK_FLAG = 0x1F3F4


def iso_from_emoji(emoji):
    """国旗絵文字から flagcdn 用のISOコードを返す。導出不能なら空文字。"""
    if not emoji:
        return ""
    # 地域指示子ペア
    ri = [c for c in emoji if _RI_BASE <= ord(c) <= _RI_BASE + 25]
    if len(ri) >= 2:
        return "".join(chr(ord(c) - _RI_BASE + ord("a")) for c in ri[:2])
    # サブディビジョン（🏴 + タグ文字列）。例: gbeng → gb-eng
    if ord(emoji[0]) == _BLACK_FLAG:
        tags = "".join(chr(ord(c) - _TAG_A + ord("a"))
                       for c in emoji if _TAG_A <= ord(c) <= _TAG_Z)
        if len(tags) >= 3:
            return f"{tags[:2]}-{tags[2:]}"
    return ""


def flag_img_url(iso):
    """ISOコードから flagcdn のSVG国旗URLを返す。空なら空文字。"""
    return f"https://flagcdn.com/{iso}.svg" if iso else ""
