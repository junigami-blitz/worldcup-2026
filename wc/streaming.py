"""日本での視聴可能な配信サービス。

実際の放映権は試合ごとに異なるが、本サイトでは「全試合で配信予定」の前提で
DAZN・ABEMA・NHK ONE を一律表示する（運用方針）。サービスを変更する場合は
このリストを編集する。
"""

STREAMING_SERVICES = [
    {"name": "DAZN", "url": "https://www.dazn.com/ja-JP/"},
    {"name": "ABEMA", "url": "https://abema.tv/"},
    {"name": "NHK ONE", "url": "https://www.nhk.jp/"},
]


def streaming_for(match=None):
    """指定試合の配信サービス一覧を返す（現状は全試合一律）。"""
    return STREAMING_SERVICES
