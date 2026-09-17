# -*- coding: utf-8 -*-
"""visualize_trades 冒烟测试：验证 CSV 解析、指标计算与仪表盘 HTML 生成。"""
import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

import visualize_trades as vt


SAMPLE_ROWS = [
    # entry_time, exit_time, side, entry_price, exit_price, cum_qty, max_qty, count, commission, gross, net
    ["2024-01-02", "2024-01-05", "LONG", "100.0", "110.0", "1.0", "1.0", "1", "0.5", "10.0", "9.5"],
    ["2024-02-02", "2024-02-10", "SHORT", "120.0", "115.0", "0.8", "0.8", "1", "0.4", "4.0", "3.6"],
    ["2024-03-02", "2024-03-04", "LONG", "130.0", "128.0", "1.0", "1.0", "1", "0.6", "-2.0", "-2.6"],
]


def _write_sample_csv(path: Path) -> None:
    header = [
        "entry_time", "exit_time", "side", "average_entry_price", "average_exit_price",
        "cumulative_quantity", "max_quantity", "count", "commission", "gross_pnl", "net_pnl",
    ]
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(SAMPLE_ROWS)


class VisualizeTradesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.csv_path = Path(self.tmp.name) / "trade_log.csv"
        _write_sample_csv(self.csv_path)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_load_trades_parses_rows(self) -> None:
        trades = vt.load_trades(self.csv_path)
        self.assertEqual(len(trades), 3)
        self.assertEqual(trades[0]["side"], "LONG")
        self.assertEqual(trades[0]["entry"], date(2024, 1, 2))
        self.assertEqual(trades[0]["exit"], date(2024, 1, 5))

    def test_build_metrics_aggregates(self) -> None:
        trades = vt.load_trades(self.csv_path)
        m = vt.build_metrics(trades)
        self.assertEqual(m["n"], 3)
        self.assertEqual(m["wins"], 2)
        self.assertEqual(m["losses"], 1)
        # 累计净盈亏 = 9.5 + 3.6 - 2.6 = 10.5
        self.assertAlmostEqual(m["total_net"], 10.5, places=6)
        self.assertEqual(m["long_count"], 2)
        self.assertEqual(m["short_count"], 1)
        # 累计曲线长度与交易笔数一致
        self.assertEqual(len(m["cum_series"]), 3)
        self.assertAlmostEqual(m["cum_series"][-1], 10.5, places=6)

    def test_build_html_produces_dashboard(self) -> None:
        trades = vt.load_trades(self.csv_path)
        m = vt.build_metrics(trades)
        doc = vt.build_html(trades, m)
        self.assertTrue(doc.lower().startswith("<!doctype html>"))
        self.assertIn("</html>", doc)
        # 三笔交易明细应全部出现
        self.assertIn("9.5", doc)
        self.assertIn("3.6", doc)
        self.assertIn("-2.6", doc)
        # 独有的甜甜圈占比图应存在
        self.assertIn("多空交易笔数占比", doc)

    def test_svg_donut_renders_segments(self) -> None:
        out = vt.svg_donut(
            [("做多", 2, vt.C_LONG), ("做空", 1, vt.C_SHORT)],
            title="多空交易笔数占比",
            center_text="3",
        )
        self.assertIn("<svg", out)
        self.assertIn("</svg>", out)
        self.assertIn(vt.C_LONG, out)
        self.assertIn(vt.C_SHORT, out)

    def test_svg_donut_zero_total_safe(self) -> None:
        self.assertEqual(
            vt.svg_donut([("做多", 0, vt.C_LONG)], title="空", center_text="0"), ""
        )


if __name__ == "__main__":
    unittest.main()
