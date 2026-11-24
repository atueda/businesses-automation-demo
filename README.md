# 業務自動化デモ｜CSV売上集計アプリ

売上CSVを選ぶだけで、**商品別・月別に自動集計**してレポートCSVを作るWebアプリです。
副業（業務自動化）の出品デモ用に作りました。

## 特徴
- Python 3 の標準ライブラリだけ使用（追加インストール不要）
- **Slackなしモード**: Webhook URLが空欄なら、このパソコンの中だけで完結
- **Slackありモード**: Webhook URLを入れると、集計完了をSlackへ自動通知
- 日本語／英語どちらのCSVヘッダーでもOK（日付, 商品名, 数量, 単価 / date, product, quantity, unit_price）

## 起動方法（Mac）
```bash
cd business-automation-demo
python3 app.py
```
ブラウザで http://localhost:8000 を開いてください。停止は Ctrl+C です。

## 使い方
1. 「サンプルCSVを読み込む」ボタンを押す（自分のCSVでもOK）
2. 必要なら Slack Webhook URL を入力
3. 「集計する」→ 商品別・月別の集計が表示され、レポートCSVをダウンロードできます

## テスト
```bash
python3 test_app.py
```

## ファイル構成
- `app.py` — サーバー本体と集計ロジック
- `index.html` — 画面
- `sample_sales.csv` — サンプル売上データ
- `test_app.py` — 集計ロジックのテスト

## 出品との対応
- Slackなし版の出品文：「Excel・CSVの手作業を自動化します」のデモ
- Slackあり版の出品文：「フォーム・Salesforceの更新をSlackへ自動通知」の集計＋通知部分のデモ
