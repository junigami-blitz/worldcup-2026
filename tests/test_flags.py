from wc.flags import iso_from_emoji, flag_img_url


def test_iso_from_regional_indicator():
    assert iso_from_emoji("🇯🇵") == "jp"
    assert iso_from_emoji("🇺🇸") == "us"
    assert iso_from_emoji("🇧🇷") == "br"
    assert iso_from_emoji("🇲🇽") == "mx"


def test_iso_from_subdivision_tag_flag():
    # 🏴 + タグ文字列(gbeng / gbsct) → gb-eng / gb-sct
    england = "\U0001F3F4\U000E0067\U000E0062\U000E0065\U000E006E\U000E0067\U000E007F"
    scotland = "\U0001F3F4\U000E0067\U000E0062\U000E0073\U000E0063\U000E0074\U000E007F"
    assert iso_from_emoji(england) == "gb-eng"
    assert iso_from_emoji(scotland) == "gb-sct"


def test_iso_empty_or_invalid():
    assert iso_from_emoji("") == ""
    assert iso_from_emoji(None) == ""
    assert iso_from_emoji("abc") == ""


def test_flag_img_url():
    assert flag_img_url("jp") == "https://flagcdn.com/jp.svg"
    assert flag_img_url("gb-eng") == "https://flagcdn.com/gb-eng.svg"
    assert flag_img_url("") == ""
