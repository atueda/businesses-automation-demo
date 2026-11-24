#!/usr/bin/env python3
"""aggregate() の簡易テスト。python3 test_app.py で実行。"""
from pathlib import Path

from app import aggregate

csv_text = Path(__file__).with_name("sample_sales.csv").read_text(encoding="utf-8")
result = aggregate(csv_text)

assert result["row_count"] == 8, result
# 合計: 12*2980 + 30*1280 + 8*2980 + 5*4980 + 25*1280 + 7*4980 + 15*2980 + 4*12800
assert result["total_amount"] == 285_660, result["total_amount"]
top = result["by_product"][0]
assert top["name"] == "ワイヤレスマウス" and top["amount"] == 104_300, top
assert [m["name"] for m in result["by_month"]] == ["2026-10", "2026-11"]
assert "商品別" in result["report_csv"]
print("OK: 集計テスト合格", result["row_count"], "件 / 合計 ¥", result["total_amount"])
