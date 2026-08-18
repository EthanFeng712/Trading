import unittest
from datetime import datetime, timedelta

from Trading.src.reports.metrics import calculate_metrics
from Trading.src.reports.metrics import calculate_annualized_return
from Trading.src.reports.metrics import calculate_max_drawdown
from Trading.src.backtest.engine import PositionSide, Trade
from Trading.src.backtest.engine import BacktestResult, EquityPoint


class MetricsTests(unittest.TestCase):
    def test_calculate_max_drawdown(self) -> None:
        equity_curve = [
            EquityPoint(datetime(2024, 1, 1), 100),
            EquityPoint(datetime(2024, 1, 2), 120),
            EquityPoint(datetime(2024, 1, 3), 90),
            EquityPoint(datetime(2024, 1, 4), 150),
            EquityPoint(datetime(2024, 1, 5), 135),
        ]
        
        max_drawdown = calculate_max_drawdown(equity_curve)
        
        self.assertAlmostEqual(max_drawdown, 0.25)
        
    def test_empty_equity_curve(self) -> None:
        max_drawdown = calculate_max_drawdown([])
        self.assertEqual(max_drawdown, 0.0)
        
    def test_no_trades_metrics(self) -> None:
        result = BacktestResult(
            initial_cash=10000,
            final_cash=10000,
            trades=[],
            equity_curve=[
                EquityPoint(datetime(2024, 1, 1), 10000),
                EquityPoint(datetime(2024, 1, 2), 10000),
                EquityPoint(datetime(2024, 1, 3), 10000),
            ]
        )
        
        metrics = calculate_metrics(result)

        self.assertEqual(metrics.total_pnl, 0.0)
        self.assertEqual(metrics.total_return, 0.0)
        self.assertEqual(metrics.annualized_return, 0.0)
        self.assertEqual(metrics.max_drawdown, 0.0)
        self.assertEqual(metrics.trade_count, 0)
        self.assertEqual(metrics.win_rate, 0.0)
        self.assertEqual(metrics.average_pnl, 0.0)
    
    def test_metrics_with_winning_and_losing_trades(self) -> None:
        trades = [
            Trade(
                side=PositionSide.LONG,
                entry_index=0,
                entry_price=100,
                quantity=1,
                buy_fee=0,
                exit_index=1,
                exit_price=120,
                commission=0,
                pnl=20,
            ),
            Trade(
                side=PositionSide.LONG,
                entry_index=2,
                entry_price=120,
                quantity=1,
                buy_fee=0,
                exit_index=3,
                exit_price=110,
                commission=0,
                pnl=-10,
            ),
        ]
        equity_curve = [
            EquityPoint(datetime(2024, 1, 1), 100),
            EquityPoint(datetime(2024, 1, 2), 120),
            EquityPoint(datetime(2024, 1, 3), 110),
        ]
        result = BacktestResult(
            initial_cash=100,
            final_cash=110,
            equity_curve=equity_curve,
            trades=trades,
        )

        metrics = calculate_metrics(result)

        self.assertAlmostEqual(metrics.total_pnl, 10.0)
        self.assertAlmostEqual(metrics.total_return, 0.1)
        self.assertAlmostEqual(metrics.max_drawdown, 10 / 120)
        self.assertEqual(metrics.trade_count, 2)
        self.assertAlmostEqual(metrics.win_rate, 0.5)
        self.assertAlmostEqual(metrics.average_pnl, 5.0)   

    def test_calculates_annualized_return(self) -> None:
        start = datetime(2024, 1, 1)
        result = BacktestResult(
            initial_cash=100,
            final_cash=121,
            equity_curve=[
                EquityPoint(start, 100),
                EquityPoint(start + timedelta(days=365, hours=6), 121),
            ],
        )
        
        metrics = calculate_metrics(result)

        self.assertAlmostEqual(metrics.annualized_return, 0.21)
     

if __name__ == "__main__":
    unittest.main()  
