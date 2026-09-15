import unittest

from src.backtest.backtest import build_strategy
from src.strategies.buy_and_hold import BuyAndHoldStrategy
from src.strategies.donchian import DonchianConfig, DonchianStrategy
from src.strategies.sma_cross import SmaCrossConfig, SmaCrossStrategy


class BuildStrategyTests(unittest.TestCase):
    def test_donchian_uses_default_parameters(self) -> None:
        strategy = build_strategy("Donchian_Channel")

        self.assertIsInstance(strategy, DonchianStrategy)
        self.assertEqual(strategy.config, DonchianConfig())

    def test_donchian_uses_given_parameters(self) -> None:
        config = DonchianConfig(window=10, target_size=0.4)

        strategy = build_strategy("Donchian_Channel", config)

        self.assertIsInstance(strategy, DonchianStrategy)
        self.assertIs(strategy.config, config)

    def test_donchian_rejects_wrong_config_type(self) -> None:
        with self.assertRaises(TypeError):
            build_strategy("Donchian_Channel", SmaCrossConfig())

    def test_sma_cross_uses_default_parameters(self) -> None:
        strategy = build_strategy("SMA_Cross")

        self.assertIsInstance(strategy, SmaCrossStrategy)
        self.assertEqual(strategy.config.fast_window, 25)
        self.assertEqual(strategy.config.slow_window, 99)
        self.assertEqual(strategy.config.target_size, 0.2)

    def test_sma_cross_uses_given_parameters(self) -> None:
        config = SmaCrossConfig(fast_window=5, slow_window=20, target_size=0.4)

        strategy = build_strategy("SMA_Cross", config)

        self.assertIs(strategy.config, config)
        self.assertEqual(strategy.config.fast_window, 5)
        self.assertEqual(strategy.config.slow_window, 20)
        self.assertEqual(strategy.config.target_size, 0.4)

    def test_sma_cross_rejects_wrong_config_type(self) -> None:
        with self.assertRaises(TypeError):
            build_strategy("SMA_Cross", (5, 20))

    def test_buy_and_hold_rejects_parameters(self) -> None:
        with self.assertRaises(ValueError):
            build_strategy("Buy_and_Hold", SmaCrossConfig())

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
