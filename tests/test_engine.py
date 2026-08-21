from datetime import datetime, timedelta
import unittest

from Trading.src.backtest.engine import SimpleBacktestEngine
from Trading.src.backtest.engine import PositionSide
from Trading.src.data.data_loader import Bar


class ScheduledStrategy:
    def __init__(self, targets: dict[int, float]) -> None:
        self.targets = targets

    def reset(self) -> None:
        pass

    def generate_signal(self, bars: list[Bar]) -> float | None:
        return self.targets.get(len(bars))


def make_bars(prices: list[float]) -> list[Bar]:
    start = datetime(2024, 1, 1)
    return [
        Bar(price, price, price, price, 1, start + timedelta(days=index))
        for index, price in enumerate(prices)
    ]


class SimpleBacktestEngineTests(unittest.TestCase):
    def test_go_long_and_close_position(self) -> None:
        engine = SimpleBacktestEngine(initial_cash=10_000, commission_rate=0.001)
        result = engine.run(make_bars([100, 100, 110]), ScheduledStrategy({1: 1.0, 2: 0.0}))
        
        self.assertEqual(len(result.trades), 1)
        self.assertEqual(result.trades[0].entry_time, datetime(2024, 1, 2))
        self.assertEqual(result.trades[0].exit_time, datetime(2024, 1, 3))
        self.assertIs(result.trades[0].side, PositionSide.LONG)
        self.assertEqual(result.trades[0].average_entry_price, 100)
        self.assertEqual(result.trades[0].average_exit_price, 110)
        self.assertAlmostEqual(result.trades[0].gross_pnl, 10_000 * 0.1)
        self.assertAlmostEqual(result.trades[0].commission, 100 * 100 * 0.001 + 100 * 110 * 0.001)
        self.assertAlmostEqual(result.trades[0].net_pnl, 1000 - 21)
        
    def test_go_short_and_close_position(self) -> None:
        engine = SimpleBacktestEngine(initial_cash=10_000, commission_rate=0.001)
        result = engine.run(make_bars([100, 100, 90]), ScheduledStrategy({1: -1.0, 2: 0.0}))
        
        self.assertEqual(len(result.trades), 1)
        self.assertIs(result.trades[0].side, PositionSide.SHORT)
        self.assertEqual(result.trades[0].average_entry_price, 100)
        self.assertEqual(result.trades[0].average_exit_price, 90)
        self.assertAlmostEqual(result.trades[0].gross_pnl, 10_000 * 0.1)
        self.assertAlmostEqual(result.trades[0].commission, 100 * 100 * 0.001 + 100 * 90 * 0.001)
        self.assertAlmostEqual(result.trades[0].net_pnl, 1000 - 19)

    def test_stop_out_position(self) -> None:
        engine = SimpleBacktestEngine(initial_cash=10_000, commission_rate=0.001)
        result = engine.run(make_bars([100, 100, 90]), ScheduledStrategy({1: 1.0}))
        
        self.assertEqual(len(result.trades), 1)
        self.assertEqual(result.trades[0].exit_time, datetime(2024, 1, 3))
        self.assertEqual(result.trades[0].average_entry_price, 100)
        self.assertEqual(result.trades[0].average_exit_price, 90)
        self.assertAlmostEqual(result.trades[0].gross_pnl, -10_000 * 0.1)
        self.assertAlmostEqual(result.trades[0].commission, 100 * 100 * 0.001 + 100 * 90 * 0.001)
        self.assertAlmostEqual(result.trades[0].net_pnl, -1000 - 19)
        
    def test_scaling_in(self) -> None:
        engine = SimpleBacktestEngine(initial_cash=10_000, commission_rate=0.001)
        result = engine.run(make_bars([100, 100, 90, 110]), ScheduledStrategy({1: 0.5, 2: 1.0, 3: 0.0}))
        
        self.assertEqual(len(result.trades), 1)
        self.assertEqual(result.trades[0].entry_time, datetime(2024, 1, 2))
        self.assertAlmostEqual(result.trades[0].cumulative_quantity, 105.5)
        self.assertAlmostEqual(result.trades[0].average_entry_price, 9995 / 105.5)
        self.assertAlmostEqual(result.trades[0].max_quantity, 105.5)
        self.assertEqual(result.trades[0].count, 3)
        self.assertAlmostEqual(result.trades[0].commission, 5 + 4.995 + 11.605)
        self.assertAlmostEqual(result.trades[0].net_pnl, 1610 - 21.6)

    def test_scaling_out(self) -> None:
        engine = SimpleBacktestEngine(initial_cash=10_000, commission_rate=0.001)
        result = engine.run(make_bars([100, 100, 110, 100]), ScheduledStrategy({1: 0.5, 2: 0.2, 3: 0.0}))
        
        self.assertEqual(len(result.trades), 1)
        self.assertEqual(result.trades[0].entry_time, datetime(2024, 1, 2))
        self.assertAlmostEqual(result.trades[0].cumulative_quantity, 10_000 * 0.5 / 100)
        self.assertAlmostEqual(result.trades[0].average_entry_price, 100)        
        self.assertAlmostEqual(result.trades[0].average_exit_price, 106.1836363636)
        self.assertEqual(result.trades[0].count, 3)
        self.assertAlmostEqual(result.trades[0].commission, 5 + 3.401 + 1.9081818182)
        self.assertAlmostEqual(result.trades[0].net_pnl, 309.1818181818 - 10.3091818182)
        
    def test_reversing_position(self) -> None:
        engine = SimpleBacktestEngine(initial_cash=10_000, commission_rate=0.001)
        result = engine.run(make_bars([100, 100, 110, 90]), ScheduledStrategy({1: 1.0, 2: -1.0, 3: 0.0}))
        
        self.assertEqual(len(result.trades), 2)
        self.assertIs(result.trades[0].side, PositionSide.LONG)
        self.assertIs(result.trades[1].side, PositionSide.SHORT)
        
    def test_invalid_targets(self) -> None:
        engine = SimpleBacktestEngine(initial_cash=10_000, commission_rate=0.001)
        with self.assertRaises(ValueError):
            engine.run(make_bars([100, 100, 110]), ScheduledStrategy({1: 1.5}))
        with self.assertRaises(ValueError):
            engine.run(make_bars([100, 100, 110]), ScheduledStrategy({1: -1.5}))

if __name__ == "__main__":
    unittest.main()
