import datetime
import unittest

from src.data.data_loader import Bar
from src.strategies.buy_and_hold import BuyAndHoldStrategy


def bar(i: int) -> Bar:
    return Bar(
        100.0, 100.0, 100.0, 100.0, 0,
        datetime.datetime(2024, 1, 1) + datetime.timedelta(days=i),
    )


class BuyAndHoldStrategyTests(unittest.TestCase):
    def test_first_signal_is_full_long(self) -> None:
        strategy = BuyAndHoldStrategy()
        self.assertEqual(strategy.generate_signal(0, None), 1.0)

    def test_no_signal_after_first_buy(self) -> None:
        strategy = BuyAndHoldStrategy()
        strategy.generate_signal(0, None)
        for i in range(1, 5):
            self.assertIsNone(strategy.generate_signal(i, bar(i - 1)))

    def test_reset_allows_rebuy(self) -> None:
        strategy = BuyAndHoldStrategy()
        strategy.generate_signal(0, None)
        self.assertIsNone(strategy.generate_signal(1, bar(0)))
        strategy.reset()
        self.assertEqual(strategy.generate_signal(2, bar(1)), 1.0)
