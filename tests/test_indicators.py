import unittest

from Trading.src.utils.indicators import simple_moving_average


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


if __name__ == "__main__":
    unittest.main()
