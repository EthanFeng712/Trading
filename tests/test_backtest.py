import unittest

from src.backtest.backtest import build_strategy
from src.strategies.buy_and_hold import BuyAndHoldStrategy
from src.strategies.sma_cross import SmaCrossStrategy


class BuildStrategyTests(unittest.TestCase):
    def test_sma_cross_uses_default_parameters(self) -> None:
        strategy = build_strategy("SMA_Cross")

        self.assertIsInstance(strategy, SmaCrossStrategy)
        self.assertEqual(strategy.fast_window, 25)
        self.assertEqual(strategy.slow_window, 99)

    def test_sma_cross_uses_given_parameters(self) -> None:
        strategy = build_strategy("SMA_Cross", (5, 20))

        self.assertEqual(strategy.fast_window, 5)
        self.assertEqual(strategy.slow_window, 20)

    def test_sma_cross_rejects_incomplete_parameters(self) -> None:
        with self.assertRaises(ValueError):
            build_strategy("SMA_Cross", (5,))

    def test_buy_and_hold_rejects_parameters(self) -> None:
        with self.assertRaises(ValueError):
            build_strategy("Buy_and_Hold", (5, 20))

    def test_buy_and_hold_needs_no_parameters(self) -> None:
        strategy = build_strategy("Buy_and_Hold")

        self.assertIsInstance(strategy, BuyAndHoldStrategy)
        self.assertEqual(strategy.generate_signal(0, None), 1.0)
        self.assertIsNone(strategy.generate_signal(1, None))

    def test_unknown_strategy_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_strategy("unknown")


if __name__ == "__main__":
    unittest.main()
