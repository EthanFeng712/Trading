import datetime
import unittest

from src.strategies.mean_reversion import MeanReversionConfig, MeanReversionStrategy
from src.data.data_loader import Bar


def bar(close: float, i: int = 0) -> Bar:
    t = datetime.datetime(2020, 1, 1) + datetime.timedelta(days=i)
    return Bar(float(close), float(close), float(close), float(close), 1.0, t)


class TestMeanReversionConfig(unittest.TestCase):
    def test_defaults(self):
        c = MeanReversionConfig()
        self.assertEqual(c.window, 20)
        self.assertEqual(c.entry_z, 2.0)
        self.assertEqual(c.exit_z, 0.5)
        self.assertEqual(c.target_size, 0.2)

    def test_invalid_window(self):
        with self.assertRaises(ValueError):
            MeanReversionConfig(window=1)

    def test_invalid_thresholds(self):
        with self.assertRaises(ValueError):
            MeanReversionConfig(entry_z=0)
        with self.assertRaises(ValueError):
            MeanReversionConfig(exit_z=2.0, entry_z=2.0)
        with self.assertRaises(ValueError):
            MeanReversionConfig(exit_z=3.0, entry_z=2.0)


class TestMeanReversionStrategy(unittest.TestCase):
    def test_warmup_none(self):
        s = MeanReversionStrategy(MeanReversionConfig(window=10, entry_z=2.0, exit_z=0.5))
        for i in range(1, 10):
            self.assertIsNone(s.generate_signal(i, bar(100 + i, i)))

    def test_flat_market_no_signal(self):
        s = MeanReversionStrategy(MeanReversionConfig(window=10, entry_z=2.0, exit_z=0.5))
        for i in range(1, 12):
            self.assertIsNone(s.generate_signal(i, bar(100, i)))

    def test_extreme_high_short(self):
        s = MeanReversionStrategy(MeanReversionConfig(window=10, entry_z=2.0, exit_z=0.5))
        for i in range(1, 11):
            s.generate_signal(i, bar(100, i))
        sig = s.generate_signal(11, bar(200, 11))
        self.assertEqual(sig, -0.2)

    def test_extreme_low_long(self):
        s = MeanReversionStrategy(MeanReversionConfig(window=10, entry_z=2.0, exit_z=0.5))
        for i in range(1, 11):
            s.generate_signal(i, bar(100, i))
        sig = s.generate_signal(11, bar(50, 11))
        self.assertEqual(sig, 0.2)

    def test_near_mean_flat(self):
        s = MeanReversionStrategy(MeanReversionConfig(window=10, entry_z=2.0, exit_z=0.5))
        vals = [100, 102, 98, 104, 96, 100, 101, 99, 103, 97]
        for i, v in enumerate(vals, start=1):
            s.generate_signal(i, bar(v, i))
        sig = s.generate_signal(11, bar(100, 11))
        self.assertEqual(sig, 0.0)

    def test_reset(self):
        s = MeanReversionStrategy(MeanReversionConfig(window=5, entry_z=2.0, exit_z=0.5))
        for i in range(1, 7):
            s.generate_signal(i, bar(100 + (i % 2) * 30, i))
        s.reset()
        self.assertIsNone(s.generate_signal(7, bar(100, 7)))


if __name__ == "__main__":
    unittest.main()
