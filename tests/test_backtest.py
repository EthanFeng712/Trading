import unittest

from Trading.src.backtest.backtest import build_strategy
from Trading.src.strategies.buy_and_hold import BuyAndHoldStrategy
from Trading.src.strategies.sma_cross import SmaCrossStrategy


class BuildStrategyTests(unittest.TestCase):
    def test_sma_cross_uses_default_parameters(self) -> None:
        strategy = build_strategy("sma_cross")

        self.assertIsInstance(strategy, SmaCrossStrategy)
        self.assertEqual(strategy.fast_window, 10)
        self.assertEqual(strategy.slow_window, 30)

    def test_sma_cross_uses_given_parameters(self) -> None:
        strategy = build_strategy("sma_cross", (5, 20))

        self.assertEqual(strategy.fast_window, 5)
        self.assertEqual(strategy.slow_window, 20)

    def test_sma_cross_rejects_incomplete_parameters(self) -> None:
        with self.assertRaises(ValueError):
            build_strategy("sma_cross", (5,))

    def test_buy_and_hold_rejects_parameters(self) -> None:
        with self.assertRaises(ValueError):
            build_strategy("buy_and_hold", (5, 20))

    def test_buy_and_hold_needs_no_parameters(self) -> None:
        self.assertIsInstance(build_strategy("buy_and_hold"), BuyAndHoldStrategy)

    def test_unknown_strategy_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_strategy("unknown")


if __name__ == "__main__":
    unittest.main()
