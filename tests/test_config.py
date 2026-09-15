from dataclasses import FrozenInstanceError
import unittest

from src.backtest.config import BacktestConfig


class BacktestConfigTests(unittest.TestCase):
    def test_default_values(self) -> None:
        config = BacktestConfig()

        self.assertEqual(config.initial_cash, 10_000.0)
        self.assertEqual(config.commission_rate, 0.001)
        self.assertEqual(config.slippage_rate, 0.0005)
        self.assertEqual(config.maintenance_margin_rate, 0.1)
        self.assertEqual(config.rebalance_tolerance, 0.001)

    def test_accepts_boundary_values(self) -> None:
        config = BacktestConfig(
            commission_rate=0.0,
            slippage_rate=0.02,
            maintenance_margin_rate=0.2,
            rebalance_tolerance=0.0,
        )

        self.assertEqual(config.slippage_rate, 0.02)
        self.assertEqual(config.maintenance_margin_rate, 0.2)

    def test_config_is_immutable(self) -> None:
        config = BacktestConfig()

        with self.assertRaises(FrozenInstanceError):
            setattr(config, "initial_cash", 20_000.0)

    def test_rejects_invalid_ranges(self) -> None:
        invalid_configs = (
            {"initial_cash": 0.0},
            {"commission_rate": -0.001},
            {"slippage_rate": -0.001},
            {"slippage_rate": 0.021},
            {"maintenance_margin_rate": -0.001},
            {"maintenance_margin_rate": 0.201},
            {"rebalance_tolerance": -0.001},
            {"rebalance_tolerance": 1.0},
        )

        for config_values in invalid_configs:
            with self.subTest(config_values=config_values):
                with self.assertRaises(ValueError):
                    BacktestConfig(**config_values)

    def test_rejects_non_finite_values(self) -> None:
        fields = (
            "initial_cash",
            "commission_rate",
            "slippage_rate",
            "maintenance_margin_rate",
            "rebalance_tolerance",
        )
        non_finite_values = (float("nan"), float("inf"), float("-inf"))

        for field in fields:
            for value in non_finite_values:
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValueError):
                        BacktestConfig(**{field: value})


if __name__ == "__main__":
    unittest.main()
