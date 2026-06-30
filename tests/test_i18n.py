from wc.i18n import jp_team, jp_round


def test_jp_team_known():
    assert jp_team("Japan") == "日本"
    assert jp_team("Spain") == "スペイン"
    assert jp_team("USA") == "アメリカ"
    assert jp_team("Ivory Coast") == "コートジボワール"


def test_jp_team_unknown_falls_back_to_english():
    assert jp_team("Atlantis") == "Atlantis"


def test_jp_team_all_48_mapped():
    # 出場48チームはすべて日本語化されている（英語のままはNG）
    teams = [
        "Algeria", "Argentina", "Australia", "Austria", "Belgium",
        "Bosnia & Herzegovina", "Brazil", "Canada", "Cape Verde", "Colombia",
        "Croatia", "Curaçao", "Czech Republic", "DR Congo", "Ecuador", "Egypt",
        "England", "France", "Germany", "Ghana", "Haiti", "Iran", "Iraq",
        "Ivory Coast", "Japan", "Jordan", "Mexico", "Morocco", "Netherlands",
        "New Zealand", "Norway", "Panama", "Paraguay", "Portugal", "Qatar",
        "Saudi Arabia", "Scotland", "Senegal", "South Africa", "South Korea",
        "Spain", "Sweden", "Switzerland", "Tunisia", "Turkey", "USA",
        "Uruguay", "Uzbekistan",
    ]
    for t in teams:
        assert jp_team(t) != t, f"{t} が日本語化されていない"


def test_jp_round_known():
    assert jp_round("Round of 32") == "ベスト32"
    assert jp_round("Round of 16") == "ベスト16"
    assert jp_round("Quarter-final") == "準々決勝"
    assert jp_round("Semi-final") == "準決勝"
    assert jp_round("Match for third place") == "3位決定戦"
    assert jp_round("Final") == "決勝"


def test_jp_round_matchday_extracts_number():
    assert jp_round("Matchday 1") == "第1節"
    assert jp_round("Matchday 14") == "第14節"


def test_jp_round_unknown_falls_back():
    assert jp_round("Mystery Round") == "Mystery Round"


from wc.i18n import jp_player


def test_jp_player_known_and_japanese():
    assert jp_player("Lionel Messi") == "リオネル・メッシ"
    assert jp_player("Kylian Mbappé") == "キリアン・ムバッペ"
    assert jp_player("Ayase Ueda") == "上田綺世"  # 日本人選手は漢字


def test_jp_player_unknown_falls_back():
    assert jp_player("John Nobody") == "John Nobody"
