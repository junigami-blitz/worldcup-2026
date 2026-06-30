"""チーム名・ラウンド名の英→日変換。未知の値は入力をそのまま返す（壊さない）。"""
import re

# 出場48チームの英→日マッピング（openfootball 2026 の name に対応）
_TEAM_JP = {
    "Algeria": "アルジェリア",
    "Argentina": "アルゼンチン",
    "Australia": "オーストラリア",
    "Austria": "オーストリア",
    "Belgium": "ベルギー",
    "Bosnia & Herzegovina": "ボスニア・ヘルツェゴビナ",
    "Brazil": "ブラジル",
    "Canada": "カナダ",
    "Cape Verde": "カーボベルデ",
    "Colombia": "コロンビア",
    "Croatia": "クロアチア",
    "Curaçao": "キュラソー",
    "Czech Republic": "チェコ",
    "DR Congo": "コンゴ民主共和国",
    "Ecuador": "エクアドル",
    "Egypt": "エジプト",
    "England": "イングランド",
    "France": "フランス",
    "Germany": "ドイツ",
    "Ghana": "ガーナ",
    "Haiti": "ハイチ",
    "Iran": "イラン",
    "Iraq": "イラク",
    "Ivory Coast": "コートジボワール",
    "Japan": "日本",
    "Jordan": "ヨルダン",
    "Mexico": "メキシコ",
    "Morocco": "モロッコ",
    "Netherlands": "オランダ",
    "New Zealand": "ニュージーランド",
    "Norway": "ノルウェー",
    "Panama": "パナマ",
    "Paraguay": "パラグアイ",
    "Portugal": "ポルトガル",
    "Qatar": "カタール",
    "Saudi Arabia": "サウジアラビア",
    "Scotland": "スコットランド",
    "Senegal": "セネガル",
    "South Africa": "南アフリカ",
    "South Korea": "韓国",
    "Spain": "スペイン",
    "Sweden": "スウェーデン",
    "Switzerland": "スイス",
    "Tunisia": "チュニジア",
    "Turkey": "トルコ",
    "USA": "アメリカ",
    "Uruguay": "ウルグアイ",
    "Uzbekistan": "ウズベキスタン",
}

_ROUND_JP = {
    "Round of 32": "ベスト32",
    "Round of 16": "ベスト16",
    "Quarter-final": "準々決勝",
    "Semi-final": "準決勝",
    "Match for third place": "3位決定戦",
    "Final": "決勝",
}

_MATCHDAY = re.compile(r"^Matchday (\d+)$")


# 主要得点者の英→日（カタカナ／日本人選手は漢字）。未知は原文フォールバック。
# ※ 大会の得点上位者を中心にキュレーション。未掲載の選手は原文（ローマ字）表示。
_PLAYER_JP = {
    "Lionel Messi": "リオネル・メッシ",
    "Erling Haaland": "アーリング・ハーランド",
    "Kylian Mbappé": "キリアン・ムバッペ",
    "Ousmane Dembélé": "ウスマン・デンベレ",
    "Vinícius Júnior": "ヴィニシウス・ジュニオール",
    "Brian Brobbey": "ブライアン・ブロベイ",
    "Cody Gakpo": "コディ・ハクポ",
    "Deniz Undav": "デニス・ウンダフ",
    "Elijah Just": "イライジャ・ジャスト",
    "Ismael Saibari": "イスマエル・サイバリ",
    "Ismaïla Sarr": "イスマイラ・サール",
    "Johan Manzambi": "ヨハン・マンザンビ",
    "Jonathan David": "ジョナサン・デイヴィッド",
    "Matheus Cunha": "マテウス・クーニャ",
    "Harry Kane": "ハリー・ケイン",
    "Kai Havertz": "カイ・ハフェルツ",
    "Yoane Wissa": "ヨアヌ・ウィサ",
    "Anthony Elanga": "アンソニー・エランガ",
    "Cristiano Ronaldo": "クリスティアーノ・ロナウド",
    "Crysencio Summerville": "クライセンシオ・サマービル",
    "Cyle Larin": "カイル・ラリン",
    "Daniel Muñoz": "ダニエル・ムニョス",
    "Ermin Mahmic": "エルミン・マフミッチ",
    "Folarin Balogun": "フォラリン・バログン",
    "Jude Bellingham": "ジュード・ベリンガム",
    "Julián Quiñones": "フリアン・キニョネス",
    "Leandro Trossard": "レアンドロ・トロサール",
    "Maxi Araújo": "マキシ・アラウホ",
    "Raúl Jiménez": "ラウル・ヒメネス",
    "Gabriel Martinelli": "ガブリエル・マルチネッリ",
    "Casemiro": "カゼミーロ",
    # 日本人選手は漢字
    "Ayase Ueda": "上田綺世",
    "Daichi Kamada": "鎌田大地",
    "Takefusa Kubo": "久保建英",
    "Kaoru Mitoma": "三笘薫",
    "Kaishu Sano": "佐野海舟",
    "Hidemasa Morita": "守田英正",
    "Ritsu Doan": "堂安律",
    "Junya Ito": "伊東純也",
    "Wataru Endo": "遠藤航",
}


def jp_team(name):
    """チーム名を日本語に。未知のチームは英語のまま返す。"""
    return _TEAM_JP.get(name, name)


def jp_player(name):
    """選手名を日本語に。未掲載の選手は原文（ローマ字）のまま返す。"""
    return _PLAYER_JP.get(name, name)


def jp_round(round_name):
    """ラウンド名を日本語に。"Matchday N" は "第N節"。未知はそのまま返す。"""
    if round_name in _ROUND_JP:
        return _ROUND_JP[round_name]
    m = _MATCHDAY.match(round_name or "")
    if m:
        return f"第{int(m.group(1))}節"
    return round_name
