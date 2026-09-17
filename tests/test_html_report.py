# -*- coding: utf-8 -*-
"""html_report 端到端冒烟测试：验证 generate_html_report 可生成合法自包含 HTML。"""
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from src.backtest.config import BacktestConfig
from src.backtest.engine import BacktestResult, EquityPoint, PositionSide, Trade
from src.reports.html_report import (
    OUTPUT_NAME,
    STRATEGY_LABELS,
    generate_html_report,
)


def _make_result() -> BacktestResult:
    """构造一个最小但字段完整、可被报告渲染的回测结果。"""
    entry = datetime(2024, 1, 2)
    exit_ = datetime(2024, 1, 5)
    trade = Trade(
        side=PositionSide.LONG,
        entry_time=entry,
        exit_time=exit_,
        average_entry_price=100.0,
        average_exit_price=110.0,
        cumulative_quantity=1.0,
        max_quantity=1.0,
        count=1,
        gross_pnl=10.0,
        commission=0.5,
        net_pnl=9.5,
    )
    curve = [
        EquityPoint(timestamp=datetime(2024, 1, 1), equity=10000.0),
        EquityPoint(timestamp=datetime(2024, 1, 5), equity=10009.5),
    ]
    return BacktestResult(
        initial_cash=10000.0,
        final_cash=10009.5,
        equity_curve=curve,
        trades=[trade],
        liquidated=False,
    )


class HtmlReportTests(unittest.TestCase):
    def test_generates_valid_html_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            result = _make_result()
            config = BacktestConfig()
            path = generate_html_report(
                result,
                config=config,
                strategy_name="SMA_Cross",
                source_path="data/sample.csv",
                output_dir=out_dir,
            )
            self.assertEqual(path, out_dir / OUTPUT_NAME)
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.lower().startswith("<!doctype html>"))
            self.assertIn("</html>", text)
            # 策略中文标签应被解析渲染
            self.assertIn(STRATEGY_LABELS["SMA_Cross"], text)

    def test_momentum_and_mean_reversion_labels_present(self) -> None:
        # 新增策略标签的回归保护：默认标签字典已包含两项
        self.assertIn("Momentum", STRATEGY_LABELS)
        self.assertIn("Mean_Reversion", STRATEGY_LABELS)
        self.assertIn("动量趋势跟踪", STRATEGY_LABELS["Momentum"])
        self.assertIn("均值回归", STRATEGY_LABELS["Mean_Reversion"])

    def test_report_renders_momentum_strategy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            result = _make_result()
            config = BacktestConfig()
            path = generate_html_report(
                result,
                config=config,
                strategy_name="Momentum",
                source_path="data/sample.csv",
                output_dir=out_dir,
            )
            text = path.read_text(encoding="utf-8")
            self.assertIn(STRATEGY_LABELS["Momentum"], text)
            # 交易明细表应至少包含一笔交易行
            self.assertIn("100.00", text)
            self.assertIn("110.00", text)


if __name__ == "__main__":
    unittest.main()
