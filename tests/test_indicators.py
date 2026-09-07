import unittest

from src.utils.indicators import simple_moving_average
from src.utils.indicators import RollingSMA


class SimpleMovingAverageTests(unittest.TestCase):
    def test_returns_none_until_the_window_is_full(self) -> None:
        self.assertEqual(
            simple_moving_average([1, 2, 3, 4], window=3),
            [None, None, 2.0, 3.0],
        )

    def test_rejects_non_positive_window(self) -> None:
        for window in (0, -1):
            with self.subTest(window=window):
                with self.assertRaises(ValueError):
                    simple_moving_average([1, 2, 3], window)

    def test_RollingSMA_updates_as_window_slides(self) -> None:
        sma = RollingSMA(window=3)
        self.assertIsNone(sma.update(1))
        self.assertIsNone(sma.update(2))
        self.assertEqual(sma.update(3), 2.0)
        self.assertEqual(sma.update(4), 3.0)
        self.assertEqual(len(sma.closes), 3)

    def test_RollingSMA_and_sma_produce_same_results(self) -> None:
        values = [1, 2, 3, 4, 5, 6, 7]
        window = 3
        sma = RollingSMA(window)
        rolling_sma_results = [sma.update(value) for value in values]
        simple_sma_results = simple_moving_average(values, window)
        self.assertEqual(rolling_sma_results, simple_sma_results)

if __name__ == "__main__":
    unittest.main()
