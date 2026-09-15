from datetime import datetime, timedelta
import unittest

from src.data.data_loader import Bar
from src.strategies.donchian import DonchianConfig, DonchianStrategy


def make_bar(day: int, high: float, low: float, close: float) -> Bar:
    return Bar(
        open=close,
        high=high,
        low=low,
        close=close,
        volume=1.0,
        timestamp=datetime(2024, 1, 1) + timedelta(days=day),
    )


def signal_stream(strategy: DonchianStrategy, closed_bars: list[Bar]) -> list[float | None]:
    return [
        strategy.generate_signal(index, closed_bars[index - 1] if index else None)
        for index in range(len(closed_bars) + 1)
    ]


class DonchianStrategyTests(unittest.TestCase):
    def test_window_must_be_a_positive_integer(self) -> None:
        for window in (0, -1, 2.5, True):
            with self.subTest(window=window):
                with self.assertRaises(ValueError):
                    DonchianConfig(window=window)

    def test_upward_breakout_uses_earlier_highs(self) -> None:
        strategy = DonchianStrategy(DonchianConfig(window=3, target_size=0.4))
        bars = [
            make_bar(0, high=10, low=8, close=9),
            make_bar(1, high=12, low=9, close=10),
            make_bar(2, high=11, low=8, close=9),
            make_bar(3, high=14, low=12, close=13),
        ]

        signals = signal_stream(strategy, bars)

        self.assertEqual(signals[:4], [None] * 4)
        self.assertEqual(signals[4], 0.4)

    def test_downward_breakout_uses_earlier_lows(self) -> None:
        strategy = DonchianStrategy(DonchianConfig(window=3, target_size=0.4))
        bars = [
            make_bar(0, high=12, low=10, close=11),
            make_bar(1, high=11, low=8, close=9),
            make_bar(2, high=13, low=9, close=10),
            make_bar(3, high=8, low=6, close=7),
        ]

        signals = signal_stream(strategy, bars)

        self.assertEqual(signals[:4], [None] * 4)
        self.assertEqual(signals[4], -0.4)

    def test_breakout_requires_close_not_just_wick(self) -> None:
        strategy = DonchianStrategy(DonchianConfig(window=3, target_size=1))
        bars = [
            make_bar(0, high=10, low=8, close=9),
            make_bar(1, high=12, low=9, close=10),
            make_bar(2, high=11, low=8, close=9),
            make_bar(3, high=15, low=9, close=11),
        ]

        self.assertIsNone(signal_stream(strategy, bars)[4])

    def test_channel_uses_highs_and_lows_not_just_closes(self) -> None:
        strategy = DonchianStrategy(DonchianConfig(window=3, target_size=1))
        bars = [
            make_bar(0, high=15, low=7, close=10),
            make_bar(1, high=12, low=8, close=11),
            make_bar(2, high=11, low=9, close=10),
            make_bar(3, high=14, low=10, close=13),
        ]

        self.assertIsNone(signal_stream(strategy, bars)[4])

    def test_touching_channel_boundary_is_not_breakout(self) -> None:
        older_bars = [
            make_bar(0, high=12, low=8, close=10),
            make_bar(1, high=11, low=9, close=10),
            make_bar(2, high=10, low=9, close=10),
        ]
        boundary_bars = (
            make_bar(3, high=13, low=9, close=12),
            make_bar(3, high=10, low=7, close=8),
        )

        for boundary_bar in boundary_bars:
            with self.subTest(close=boundary_bar.close):
                strategy = DonchianStrategy(DonchianConfig(window=3, target_size=1))
                self.assertIsNone(signal_stream(strategy, older_bars + [boundary_bar])[4])

    def test_expired_high_no_longer_blocks_breakout(self) -> None:
        strategy = DonchianStrategy(DonchianConfig(window=2, target_size=1))
        bars = [
            make_bar(0, high=20, low=8, close=10),
            make_bar(1, high=12, low=8, close=10),
            make_bar(2, high=11, low=8, close=10),
            make_bar(3, high=13, low=10, close=13),
        ]

        signals = signal_stream(strategy, bars)

        self.assertEqual(signals[:4], [None] * 4)
        self.assertEqual(signals[4], 1)

    def test_waits_for_full_older_window_before_breakout(self) -> None:
        strategy = DonchianStrategy(DonchianConfig(window=3, target_size=0.4))
        bars = [
            make_bar(0, high=10, low=8, close=9),
            make_bar(1, high=11, low=9, close=10),
            make_bar(2, high=13, low=11, close=12),
        ]

        self.assertEqual(signal_stream(strategy, bars), [None] * 4)

    def test_reset_clears_window_before_second_run(self) -> None:
        strategy = DonchianStrategy(DonchianConfig(window=3, target_size=0.4))
        bars = [
            make_bar(0, high=10, low=8, close=9),
            make_bar(1, high=12, low=9, close=10),
            make_bar(2, high=11, low=8, close=9),
            make_bar(3, high=14, low=12, close=13),
        ]

        first_signals = signal_stream(strategy, bars)
        strategy.reset()

        self.assertEqual(len(strategy.last_maximums), 0)
        self.assertEqual(len(strategy.last_minimums), 0)
        self.assertEqual(signal_stream(strategy, bars), first_signals)


if __name__ == "__main__":
    unittest.main()
