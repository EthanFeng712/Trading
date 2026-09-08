from datetime import datetime, timedelta
import unittest

from src.backtest.engine import SimpleBacktestEngine
from src.backtest.engine import PositionSide
from src.data.data_loader import Bar


class ScheduledStrategy:
    def __init__(self, targets: dict[int, float]) -> None:
        self.targets = targets

    def reset(self) -> None:
        pass

    def generate_signal(self, index: int, _previous_bar: Bar | None) -> float | None:
        return self.targets.get(index)


def make_bars(prices: list[float]) -> list[Bar]:
    return [
        make_bar(index, price, price, price, price)
        for index, price in enumerate(prices)
    ]


def make_bar(
    day: int,
    open_price: float,
    high_price: float,
    low_price: float,
    close_price: float,
) -> Bar:
    return Bar(
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
        volume=1,
        timestamp=datetime(2024, 1, 1) + timedelta(days=day),
    )


class SimpleBacktestEngineTests(unittest.TestCase):
    def test_go_long_and_close_position(self) -> None:
        engine = SimpleBacktestEngine(
            initial_cash=10_000,
            commission_rate=0.001,
            slippage_rate=0.0,
        )
        result = engine.run(make_bars([100, 100, 110]), ScheduledStrategy({1: 1.0, 2: 0.0}))

        quantity = 10_000 / (100 * (1 + 0.001))
        gross_pnl = quantity * (110 - 100)
        commission = quantity * (100 + 110) * 0.001

        self.assertEqual(len(result.trades), 1)
        self.assertEqual(result.trades[0].entry_time, datetime(2024, 1, 2))
        self.assertEqual(result.trades[0].exit_time, datetime(2024, 1, 3))
        self.assertIs(result.trades[0].side, PositionSide.LONG)
        self.assertFalse(result.liquidated)
        self.assertEqual(result.trades[0].average_entry_price, 100)
        self.assertEqual(result.trades[0].average_exit_price, 110)
        self.assertAlmostEqual(result.trades[0].gross_pnl, gross_pnl)
        self.assertAlmostEqual(result.trades[0].commission, commission)
        self.assertAlmostEqual(result.trades[0].net_pnl, gross_pnl - commission)

    def test_go_short_and_close_position(self) -> None:
        engine = SimpleBacktestEngine(
            initial_cash=10_000,
            commission_rate=0.001,
            slippage_rate=0.0,
        )
        result = engine.run(make_bars([100, 100, 90]), ScheduledStrategy({1: -1.0, 2: 0.0}))

        self.assertEqual(len(result.trades), 1)
        self.assertIs(result.trades[0].side, PositionSide.SHORT)
        self.assertEqual(result.trades[0].average_entry_price, 100)
        self.assertEqual(result.trades[0].average_exit_price, 90)
        self.assertAlmostEqual(result.trades[0].gross_pnl, 10_000 * 0.1)
        self.assertAlmostEqual(result.trades[0].commission, 100 * 100 * 0.001 + 100 * 90 * 0.001)
        self.assertAlmostEqual(result.trades[0].net_pnl, 1000 - 19)

    def test_stop_out_position(self) -> None:
        engine = SimpleBacktestEngine(
            initial_cash=10_000,
            commission_rate=0.001,
            slippage_rate=0.0,
        )
        result = engine.run(make_bars([100, 100, 90]), ScheduledStrategy({1: 1.0}))

        quantity = 10_000 / (100 * (1 + 0.001))
        gross_pnl = quantity * (90 - 100)
        commission = quantity * (100 + 90) * 0.001

        self.assertEqual(len(result.trades), 1)
        self.assertEqual(result.trades[0].exit_time, datetime(2024, 1, 3))
        self.assertEqual(result.trades[0].average_entry_price, 100)
        self.assertEqual(result.trades[0].average_exit_price, 90)
        self.assertAlmostEqual(result.trades[0].gross_pnl, gross_pnl)
        self.assertAlmostEqual(result.trades[0].commission, commission)
        self.assertAlmostEqual(result.trades[0].net_pnl, gross_pnl - commission)

    def test_slippage_uses_unfavorable_entry_and_exit_prices(self) -> None:
        engine = SimpleBacktestEngine(
            initial_cash=10_000,
            commission_rate=0.0,
            slippage_rate=0.01,
        )
        result = engine.run(
            make_bars([100, 100, 100]),
            ScheduledStrategy({1: 0.5, 2: 0.0}),
        )

        trade = result.trades[0]
        self.assertAlmostEqual(trade.average_entry_price, 101.0)
        self.assertAlmostEqual(trade.average_exit_price, 99.0)
        self.assertAlmostEqual(trade.gross_pnl, -100.0)
        self.assertAlmostEqual(result.final_cash, 9_900.0)

    def test_end_of_backtest_close_applies_slippage(self) -> None:
        engine = SimpleBacktestEngine(
            initial_cash=10_000,
            commission_rate=0.0,
            slippage_rate=0.01,
        )
        result = engine.run(
            make_bars([100, 100, 100]),
            ScheduledStrategy({1: 0.5}),
        )

        self.assertAlmostEqual(result.trades[0].average_exit_price, 99.0)
        self.assertAlmostEqual(result.final_cash, 9_900.0)
        self.assertAlmostEqual(result.equity_curve[-1].equity, 9_900.0)

    def test_rebalance_tolerance_ignores_small_cost_drift(self) -> None:
        engine = SimpleBacktestEngine(
            initial_cash=10_000,
            commission_rate=0.001,
            slippage_rate=0.0005,
        )
        result = engine.run(
            make_bars([100, 100, 100]),
            ScheduledStrategy({1: 0.5, 2: 0.5}),
        )

        self.assertEqual(result.trades[0].count, 2)

    def test_scaling_in(self) -> None:
        engine = SimpleBacktestEngine(
            initial_cash=10_000,
            commission_rate=0.001,
            slippage_rate=0.0,
        )
        result = engine.run(make_bars([100, 100, 90, 110]), ScheduledStrategy({1: 0.5, 2: 1.0, 3: 0.0}))

        first_quantity = 50
        cash_after_first_order = 10_000 - first_quantity * 100 * (1 + 0.001)
        second_quantity = cash_after_first_order / (90 * (1 + 0.001))
        total_quantity = first_quantity + second_quantity
        total_entry_value = first_quantity * 100 + second_quantity * 90
        gross_pnl = first_quantity * (110 - 100) + second_quantity * (110 - 90)
        commission = (first_quantity * 100 * 0.001 + second_quantity * 90 * 0.001 + total_quantity * 110 * 0.001)

        self.assertEqual(len(result.trades), 1)
        self.assertEqual(result.trades[0].entry_time, datetime(2024, 1, 2))
        self.assertAlmostEqual(result.trades[0].cumulative_quantity, total_quantity)
        self.assertAlmostEqual(result.trades[0].average_entry_price, total_entry_value / total_quantity)
        self.assertAlmostEqual(result.trades[0].max_quantity, total_quantity)
        self.assertEqual(result.trades[0].count, 3)
        self.assertAlmostEqual(result.trades[0].commission, commission)
        self.assertAlmostEqual(result.trades[0].net_pnl, gross_pnl - commission)

    def test_full_long_order_reserves_cash_for_commission(self) -> None:
        engine = SimpleBacktestEngine(initial_cash=10_000, commission_rate=0.001)

        engine.opt(make_bars([100])[0], quantity=100, fill_price=100)

        expected_quantity = 10_000 / (100 * (1 + 0.001))
        self.assertAlmostEqual(engine.position.quantity, expected_quantity)
        self.assertAlmostEqual(engine.cash, 0.0)

    def test_partial_short_close_is_not_limited_by_available_cash(self) -> None:
        engine = SimpleBacktestEngine(initial_cash=10_000, commission_rate=0.0)
        bar = make_bars([100])[0]
        engine.opt(bar, quantity=-100, fill_price=100)

        engine.opt(bar, quantity=20, fill_price=1_001)

        self.assertAlmostEqual(engine.position.quantity, -80)

    def test_intrabar_high_triggers_short_liquidation(self) -> None:
        engine = SimpleBacktestEngine(
            initial_cash=10_000,
            commission_rate=0.0,
            slippage_rate=0.0,
            maintenance_margin_rate=0.1,
        )
        bars = [
            make_bar(0, 100, 100, 100, 100),
            make_bar(1, 100, 100, 100, 100),
            make_bar(2, 170, 190, 160, 170),
            make_bar(3, 100, 100, 100, 100),
        ]

        result = engine.run(bars, ScheduledStrategy({1: -1.0, 3: -1.0}))

        liquidation_price = 20_000 / (100 * (1 + 0.1))
        self.assertEqual(len(result.trades), 1)
        self.assertEqual(len(result.equity_curve), len(bars))
        self.assertTrue(result.liquidated)
        self.assertEqual(result.equity_curve[-1].timestamp, bars[-1].timestamp)
        self.assertAlmostEqual(result.equity_curve[-1].equity, result.final_cash)
        self.assertAlmostEqual(result.trades[0].average_exit_price, liquidation_price)
        self.assertAlmostEqual(result.final_cash, 20_000 - 100 * liquidation_price)

    def test_gap_open_uses_open_price_for_short_liquidation(self) -> None:
        engine = SimpleBacktestEngine(
            initial_cash=10_000,
            commission_rate=0.0,
            slippage_rate=0.0,
            maintenance_margin_rate=0.1,
        )
        bars = [
            make_bar(0, 100, 100, 100, 100),
            make_bar(1, 100, 100, 100, 100),
            make_bar(2, 190, 195, 185, 190),
            make_bar(3, 100, 100, 100, 100),
        ]

        result = engine.run(bars, ScheduledStrategy({1: -1.0, 3: -1.0}))

        self.assertEqual(len(result.trades), 1)
        self.assertEqual(len(result.equity_curve), len(bars))
        self.assertTrue(result.liquidated)
        self.assertEqual(result.equity_curve[-1].timestamp, bars[-1].timestamp)
        self.assertAlmostEqual(result.equity_curve[-1].equity, result.final_cash)
        self.assertAlmostEqual(result.trades[0].average_exit_price, 190)
        self.assertAlmostEqual(result.final_cash, 1_000)

    def test_short_liquidation_applies_slippage_and_commission(self) -> None:
        engine = SimpleBacktestEngine(
            initial_cash=10_000,
            commission_rate=0.001,
            slippage_rate=0.01,
            maintenance_margin_rate=0.1,
        )
        bars = [
            make_bar(0, 100, 100, 100, 100),
            make_bar(1, 100, 100, 100, 100),
            make_bar(2, 170, 190, 160, 170),
        ]

        result = engine.run(bars, ScheduledStrategy({1: -1.0}))

        quantity = 100
        entry_price = 100 * (1 - 0.01)
        entry_commission = entry_price * quantity * 0.001
        cash_after_entry = 10_000 + entry_price * quantity - entry_commission
        liquidation_price = cash_after_entry / (quantity * (1 + 0.1))
        exit_price = liquidation_price * (1 + 0.01)
        exit_commission = exit_price * quantity * 0.001
        expected_cash = cash_after_entry - exit_price * quantity - exit_commission

        trade = result.trades[0]
        self.assertAlmostEqual(trade.average_entry_price, entry_price)
        self.assertAlmostEqual(trade.average_exit_price, exit_price)
        self.assertAlmostEqual(
            trade.commission,
            entry_commission + exit_commission,
        )
        self.assertAlmostEqual(result.final_cash, expected_cash)

    def test_scaling_out(self) -> None:
        engine = SimpleBacktestEngine(
            initial_cash=10_000,
            commission_rate=0.001,
            slippage_rate=0.0,
        )
        result = engine.run(make_bars([100, 100, 110, 100]), ScheduledStrategy({1: 0.5, 2: 0.2, 3: 0.0}))

        entry_quantity = 10_000 * 0.5 / 100
        cash_after_entry = 10_000 - entry_quantity * 100 * (1 + 0.001)
        equity_at_scale_out = cash_after_entry + entry_quantity * 110
        remaining_quantity = equity_at_scale_out * 0.2 / 110
        scaled_out_quantity = entry_quantity - remaining_quantity
        average_exit_price = (scaled_out_quantity * 110 + remaining_quantity * 100) / entry_quantity
        gross_pnl = scaled_out_quantity * (110 - 100)
        commission = (entry_quantity * 100 + scaled_out_quantity * 110 + remaining_quantity * 100) * 0.001

        self.assertEqual(len(result.trades), 1)
        self.assertEqual(result.trades[0].entry_time, datetime(2024, 1, 2))
        self.assertAlmostEqual(result.trades[0].cumulative_quantity, entry_quantity)
        self.assertAlmostEqual(result.trades[0].average_entry_price, 100)
        self.assertAlmostEqual(result.trades[0].average_exit_price, average_exit_price)
        self.assertEqual(result.trades[0].count, 3)
        self.assertAlmostEqual(result.trades[0].commission, commission)
        self.assertAlmostEqual(result.trades[0].net_pnl, gross_pnl - commission)

    def test_reversing_position(self) -> None:
        engine = SimpleBacktestEngine(
            initial_cash=10_000,
            commission_rate=0.001,
            slippage_rate=0.0,
        )
        result = engine.run(make_bars([100, 100, 110, 90]), ScheduledStrategy({1: 1.0, 2: -1.0, 3: 0.0}))

        self.assertEqual(len(result.trades), 2)
        self.assertIs(result.trades[0].side, PositionSide.LONG)
        self.assertIs(result.trades[1].side, PositionSide.SHORT)

    def test_invalid_targets(self) -> None:
        engine = SimpleBacktestEngine(initial_cash=10_000, commission_rate=0.001)
        invalid_targets = (
            -1.5,
            1.5,
            float("nan"),
            float("inf"),
            float("-inf"),
        )

        for target in invalid_targets:
            with self.subTest(target=target):
                with self.assertRaises(ValueError):
                    engine.run(
                        make_bars([100, 100, 110]),
                        ScheduledStrategy({1: target}),
                    )

    def test_invalid_slippage_rates(self) -> None:
        for slippage_rate in (-0.001, 0.021):
            with self.subTest(slippage_rate=slippage_rate):
                with self.assertRaises(ValueError):
                    SimpleBacktestEngine(slippage_rate=slippage_rate)

    def test_invalid_maintenance_margin_rates(self) -> None:
        for maintenance_margin_rate in (-0.001, 0.201):
            with self.subTest(maintenance_margin_rate=maintenance_margin_rate):
                with self.assertRaises(ValueError):
                    SimpleBacktestEngine(
                        maintenance_margin_rate=maintenance_margin_rate,
                    )

if __name__ == "__main__":
    unittest.main()
