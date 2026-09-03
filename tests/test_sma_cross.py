from datetime import datetime, timedelta
import unittest

from Trading.src.data.data_loader import Bar
from Trading.src.strategies.sma_cross import SmaCrossStrategy


def make_bars(closes: list[float]) -> list[Bar]:
    start = datetime(2024, 1, 1)
    return [
        Bar(price, price, price, price, 0, start + timedelta(days=index))
        for index, price in enumerate(closes)
    ]


def generate_signal_stream(strategy: SmaCrossStrategy, bars: list[Bar]) -> float | None:
    previous_bar: Bar | None = None
    signal: float | None = None

    for index, bar in enumerate(bars):
        signal = strategy.generate_signal(index, previous_bar)
        previous_bar = bar

    return strategy.generate_signal(len(bars), previous_bar)


class SmaCrossStrategyTests(unittest.TestCase):
    def test_short_history_returns_none_without_error(self) -> None:
        strategy = SmaCrossStrategy(fast_window=2, slow_window=3)
        bars = [
            Bar(100, 100, 100, 100, 0, datetime(2024, 1, 1)),
            Bar(101, 101, 101, 101, 0, datetime(2024, 1, 1) + timedelta(days=1)),
        ]

        signal = generate_signal_stream(strategy, bars)

        self.assertIsNone(signal)

    def test_upward_cross_returns_buy(self) -> None:
        strategy = SmaCrossStrategy(fast_window=2, slow_window=3)

        signal = generate_signal_stream(strategy, make_bars([3, 2, 1, 2, 3]))

        self.assertEqual(signal, 0.2)

    def test_downward_cross_returns_sell(self) -> None:
        strategy = SmaCrossStrategy(fast_window=2, slow_window=3)

        signal = generate_signal_stream(strategy, make_bars([1, 2, 3, 2, 1]))

        self.assertEqual(signal, -0.2)

    def test_reset_clears_state(self) -> None:
        strategy = SmaCrossStrategy(fast_window=2, slow_window=3)
        generate_signal_stream(strategy, make_bars([3, 2, 1, 2, 3]))

        self.assertIsNotNone(strategy.fast.sma)
        self.assertIsNotNone(strategy.slow.sma)

        strategy.reset()

        self.assertIsNone(strategy.fast.sma)
        self.assertIsNone(strategy.slow.sma)
        self.assertEqual(strategy.fast_sma, [])
        self.assertEqual(strategy.slow_sma, [])
        self.assertEqual(len(strategy.fast.closes), 0)
        self.assertEqual(len(strategy.slow.closes), 0)

if __name__ == "__main__":
    unittest.main()
