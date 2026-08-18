from datetime import datetime, timedelta
import unittest

from Trading.src.backtest.engine import SimpleBacktestEngine
from Trading.src.data.data_loader import Bar
from Trading.src.strategies.base import Signal


class ScheduledStrategy:
    def __init__(self, signals: dict[int, Signal]) -> None:
        self.signals = signals

    def reset(self) -> None:
        pass

    def generate_signal(self, bars: list[Bar]) -> Signal:
        return self.signals.get(len(bars), Signal.NONE)


def make_bars(prices: list[float]) -> list[Bar]:
    start = datetime(2024, 1, 1)
    return [
        Bar(price, price, price, price, 1, start + timedelta(days=index))
        for index, price in enumerate(prices)
    ]


class SimpleBacktestEngineTests(unittest.TestCase):
    def test_proportional_position_includes_buy_fee(self) -> None:
        engine = SimpleBacktestEngine(initial_cash=10_000, commission_rate=0.001, position_size=0.5)
        result = engine.run(make_bars([100, 100, 110]), ScheduledStrategy({1: Signal.BUY, 2: Signal.SELL}))

        trade = result.trades[0]
        expected_quantity = 5_000 / 100.1
        expected_commission = expected_quantity * (0.1 + 0.11)
        expected_pnl = (110 - 100) * expected_quantity - expected_commission

        self.assertAlmostEqual(trade.quantity, expected_quantity)
        self.assertAlmostEqual(trade.commission, expected_commission)
        self.assertAlmostEqual(trade.pnl, expected_pnl)
        self.assertAlmostEqual(result.final_cash, 10_000 + expected_pnl)

    def test_forced_liquidation_charges_exit_fee(self) -> None:
        engine = SimpleBacktestEngine(initial_cash=10_000, commission_rate=0.001, position_size=0.5)
        result = engine.run(make_bars([100, 100, 110]), ScheduledStrategy({1: Signal.BUY}))

        trade = result.trades[0]
        self.assertEqual(trade.exit_index, 2)
        self.assertEqual(trade.exit_price, 110)
        self.assertAlmostEqual(trade.commission, trade.quantity * (0.1 + 0.11))
        self.assertAlmostEqual(result.final_cash, 10_000 + trade.pnl)

    def test_signal_executes_at_the_next_bar_open(self) -> None:
        bars = [
            Bar(90, 100, 80, 95, 1, datetime(2024, 1, 1)),
            Bar(100, 110, 90, 105, 1, datetime(2024, 1, 2)),
            Bar(110, 120, 100, 115, 1, datetime(2024, 1, 3)),
        ]
        engine = SimpleBacktestEngine(commission_rate=0)

        result = engine.run(bars, ScheduledStrategy({1: Signal.BUY, 2: Signal.SELL}))

        trade = result.trades[0]
        self.assertEqual(trade.entry_index, 1)
        self.assertEqual(trade.entry_price, 100)
        self.assertEqual(trade.exit_index, 2)
        self.assertEqual(trade.exit_price, 110)

    def test_buy_signal_does_not_open_a_second_position(self) -> None:
        engine = SimpleBacktestEngine(commission_rate=0)

        result = engine.run(
            make_bars([100, 100, 100, 100]),
            ScheduledStrategy({1: Signal.BUY, 2: Signal.BUY, 3: Signal.SELL}),
        )

        self.assertEqual(len(result.trades), 1)
        self.assertEqual(result.trades[0].entry_index, 1)

    def test_invalid_account_configuration_is_rejected(self) -> None:
        invalid_configs = [
            {"initial_cash": 0},
            {"commission_rate": -0.001},
            {"position_size": 0},
            {"position_size": 1.1},
        ]

        for config in invalid_configs:
            with self.subTest(config=config):
                with self.assertRaises(ValueError):
                    SimpleBacktestEngine(**config)


if __name__ == "__main__":
    unittest.main()
