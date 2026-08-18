from datetime import datetime, timedelta
import unittest

from Trading.src.data.data_loader import Bar
from Trading.src.strategies.base import Signal
from Trading.src.strategies.sma_cross import SmaCrossStrategy


def make_bars(closes: list[float]) -> list[Bar]:
    start = datetime(2024, 1, 1)
    return [
        Bar(price, price, price, price, 0, start + timedelta(days=index))
        for index, price in enumerate(closes)
    ]


class SmaCrossStrategyTests(unittest.TestCase):
    def test_short_history_returns_none_without_error(self) -> None:
        strategy = SmaCrossStrategy(fast_window=2, slow_window=3)
        bars = [
            Bar(100, 100, 100, 100, 0, datetime(2024, 1, 1)),
            Bar(101, 101, 101, 101, 0, datetime(2024, 1, 1) + timedelta(days=1)),
        ]

        signal = strategy.generate_signal(bars)

        self.assertIs(signal, Signal.NONE)

    def test_upward_cross_returns_buy(self) -> None:
        strategy = SmaCrossStrategy(fast_window=2, slow_window=3)

        signal = strategy.generate_signal(make_bars([3, 2, 1, 2, 3]))

        self.assertIs(signal, Signal.BUY)

    def test_downward_cross_returns_sell(self) -> None:
        strategy = SmaCrossStrategy(fast_window=2, slow_window=3)

        signal = strategy.generate_signal(make_bars([1, 2, 3, 2, 1]))

        self.assertIs(signal, Signal.SELL)


if __name__ == "__main__":
    unittest.main()
