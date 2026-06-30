# World Cup 2026 解説サイト

2026 FIFAワールドカップ（カナダ・メキシコ・USA共催）の試合結果・順位・ランキング・ニュース・ハイライトを無料データソースから自動更新する静的サイト。

## 構成
- データ取得・集計: `wc/`（Python標準ライブラリ + curl）
- 生成データ: `data/*.json`
- 仕様: `docs/superpowers/specs/2026-06-30-worldcup-2026-site-design.md`

## データ更新

    python -m wc.update_data

## サイト生成

    python -m wc.build_site
    # site/ に index/groups/knockout/rankings.html + assets/style.css を生成

## ローカルプレビュー

    cd site && python -m http.server 8765
    # http://localhost:8765/ を開く

## テスト

    pytest
