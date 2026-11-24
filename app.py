#!/usr/bin/env python3
"""業務自動化デモアプリ

CSV（売上データ）をアップロードすると、商品別・月別に自動集計して
レポートCSVを生成します。外部ライブラリは不要で、Python 3 の標準
ライブラリだけで動きます。

Slack Webhook URL を入力した場合だけ、集計完了を Slack に通知します
（Slackあり版）。空欄なら、このパソコンの中だけで完結します
（Slackなし版）。

使い方:
    python3 app.py
    ブラウザで http://localhost:8000 を開く
"""

import csv
import io
import json
import urllib.request
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PORT = 8000

# 日本語 / 英語どちらのヘッダーでも受け付ける
HEADER_ALIASES = {
    "date": "date", "日付": "date", "年月日": "date",
    "product": "product", "商品名": "product", "商品": "product", "品目": "product",
    "quantity": "quantity", "数量": "quantity", "個数": "quantity",
    "unit_price": "unit_price", "単価": "unit_price", "価格": "unit_price",
}


def parse_rows(csv_text: str) -> list[dict]:
    """CSVテキストを {date, product, quantity, unit_price, amount} の行に変換する。"""
    reader = csv.DictReader(io.StringIO(csv_text))
    if reader.fieldnames is None:
        raise ValueError("CSVにヘッダー行がありません")
    header_map = {}
    for raw in reader.fieldnames:
        key = HEADER_ALIASES.get((raw or "").strip())
        if key:
            header_map[raw] = key
    missing = {"date", "product", "quantity", "unit_price"} - set(header_map.values())
    if missing:
        raise ValueError(
            "必要な列が見つかりません: " + ", ".join(sorted(missing))
            + "（必要な列: 日付, 商品名, 数量, 単価）"
        )
    rows = []
    for i, raw_row in enumerate(reader, start=2):
        row = {header_map[k]: (v or "").strip() for k, v in raw_row.items() if k in header_map}
        if not any(row.values()):
            continue
        try:
            quantity = float(row["quantity"])
            unit_price = float(row["unit_price"])
        except ValueError:
            raise ValueError(f"{i}行目: 数量と単価は数字で入力してください")
        rows.append({
            "date": row["date"],
            "product": row["product"],
            "quantity": quantity,
            "unit_price": unit_price,
            "amount": quantity * unit_price,
        })
    if not rows:
        raise ValueError("データ行がありません")
    return rows


def aggregate(csv_text: str) -> dict:
    """商品別・月別に集計し、レポートCSVも作って返す。"""
    rows = parse_rows(csv_text)
    by_product = defaultdict(lambda: {"quantity": 0.0, "amount": 0.0})
    by_month = defaultdict(lambda: {"quantity": 0.0, "amount": 0.0})
    for r in rows:
        by_product[r["product"]]["quantity"] += r["quantity"]
        by_product[r["product"]]["amount"] += r["amount"]
        month = r["date"][:7]  # YYYY-MM
        by_month[month]["quantity"] += r["quantity"]
        by_month[month]["amount"] += r["amount"]

    def fmt(table):
        return [
            {"name": k, "quantity": v["quantity"], "amount": round(v["amount"])}
            for k, v in sorted(table.items(), key=lambda kv: kv[1]["amount"], reverse=True)
        ]

    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["区分", "名前", "数量", "金額"])
    for item in fmt(by_product):
        writer.writerow(["商品別", item["name"], item["quantity"], item["amount"]])
    for item in sorted(fmt(by_month), key=lambda x: x["name"]):
        writer.writerow(["月別", item["name"], item["quantity"], item["amount"]])
    total = round(sum(r["amount"] for r in rows))

    return {
        "row_count": len(rows),
        "total_amount": total,
        "by_product": fmt(by_product),
        "by_month": sorted(fmt(by_month), key=lambda x: x["name"]),
        "report_csv": out.getvalue(),
    }


def notify_slack(webhook_url: str, result: dict) -> str:
    """Slack Incoming Webhook へ集計完了を通知する。結果文字列を返す。"""
    text = (
        f"📊 売上集計が完了しました\n"
        f"・データ件数: {result['row_count']}件\n"
        f"・合計金額: ¥{result['total_amount']:,}\n"
        f"・商品数: {len(result['by_product'])}種類"
    )
    req = urllib.request.Request(
        webhook_url,
        data=json.dumps({"text": text}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            return "通知しました" if res.status == 200 else f"通知失敗 (HTTP {res.status})"
    except Exception as e:  # 通知失敗でも集計結果は返す
        return f"通知失敗: {e}"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = (BASE_DIR / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/sample.csv":
            body = (BASE_DIR / "sample_sales.csv").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path != "/api/aggregate":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
            result = aggregate(payload.get("csv_text", ""))
            webhook = (payload.get("slack_webhook_url") or "").strip()
            result["slack"] = notify_slack(webhook, result) if webhook else "なし（Slackなしモード）"
            self._json(200, result)
        except ValueError as e:
            self._json(400, {"error": str(e)})
        except Exception as e:
            self._json(500, {"error": f"サーバーエラー: {e}"})

    def _json(self, status, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print(f"業務自動化デモを起動しました: http://localhost:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
