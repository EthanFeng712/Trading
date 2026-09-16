import unittest

from src.strategies.buy_and_hold import BuyAndHoldStrategy


class BuyAndHoldStrategyTests(unittest.TestCase):
    def test_buys_once_and_then_holds(self) -> None:
        strategy = BuyAndHoldStrategy()

        self.assertEqual(strategy.generate_signal(0, None), 1.0)
        self.assertIsNone(strategy.generate_signal(1, None))

    def test_reset_allows_a_second_run(self) -> None:
        strategy = BuyAndHoldStrategy()
        strategy.generate_signal(0, None)

        strategy.reset()

        self.assertEqual(strategy.generate_signal(0, None), 1.0)


if __name__ == "__main__":
    unittest.main()
