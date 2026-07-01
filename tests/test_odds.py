import json

from wc.odds import parse_odds, build_odds_url, normalize_odds_name, implied_probs

ODDS_JSON = json.dumps([
    {
        "id": "abc", "commence_time": "2026-06-11T19:00:00Z",
        "home_team": "Mexico", "away_team": "South Korea",
        "bookmakers": [
            {"key": "bet365", "markets": [
                {"key": "h2h", "outcomes": [
                    {"name": "Mexico", "price": 1.80},
                    {"name": "South Korea", "price": 4.50},
                    {"name": "Draw", "price": 3.40},
                ]},
                {"key": "totals", "outcomes": []},
            ]},
            {"key": "williamhill", "markets": [
                {"key": "h2h", "outcomes": [
                    {"name": "Mexico", "price": 1.90},
                    {"name": "South Korea", "price": 4.20},
                    {"name": "Draw", "price": 3.30},
                ]},
            ]},
        ],
    }
])


def test_parse_odds_averages_and_probs():
    ev = parse_odds(ODDS_JSON)[0]
    assert ev["home"] == "Mexico"
    assert ev["away"] == "South Korea"
    assert ev["date"] == "2026-06-11"
    assert ev["books"] == 2
    # 平均オッズ: home=(1.80+1.90)/2=1.85
    assert ev["odds"]["home"] == 1.85
    # 勝率は正規化されて合計100前後、home が最有力
    p = ev["probs"]
    assert p["home"] > p["draw"] > p["away"]
    assert 98 <= p["home"] + p["draw"] + p["away"] <= 102


def test_implied_probs_normalized():
    probs = implied_probs(2.0, 4.0, 4.0)  # 50%,25%,25% before margin → 正規化で 50/25/25
    assert probs["home"] == 50
    assert probs["draw"] == 25
    assert probs["away"] == 25


def test_parse_odds_error_object_returns_empty():
    assert parse_odds('{"message": "invalid api key"}') == []
    assert parse_odds("<broken") == []


def test_build_odds_url():
    url = build_odds_url("KEY123")
    assert "soccer_fifa_world_cup" in url
    assert "apiKey=KEY123" in url
    assert "markets=h2h" in url
    assert "oddsFormat=decimal" in url


def test_normalize_odds_name():
    assert normalize_odds_name("Korea Republic") == "South Korea"
    assert normalize_odds_name("Japan") == "Japan"
