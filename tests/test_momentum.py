import datetime
import unittest

from src.strategies.momentum import MomentumConfig, MomentumStrategy
from src.data.data_loader import Bar


def bar(close: float, i: int = 0) -> Bar:
    t = datetime.datetime(2020, 1, 1) + datetime.timedelta(days=i)
    return Bar(float(close), float(close), float(close), float(close), 1.0, t)


class TestMomentumConfig(unittest.TestCase):
    def test_defaults(self):
        c = MomentumConfig()
        self.assertEqual(c.lookback, 20)
        self.assertEqual(c.threshold, 0.0)
        self.assertEqual(c.target_size, 0.2)

    def test_invalid_lookback(self):
        with self.assertRaises(ValueError):
            MomentumConfig(lookback=0)
        with self.assertRaises(ValueError):
            MomentumConfig(lookback=-5)

    def test_invalid_threshold(self):
        with self.assertRaises(ValueError):
            MomentumConfig(threshold=-0.1)

    def test_invalid_target(self):
        with self.assertRaises(ValueError):
            MomentumConfig(target_size=0)
        with self.assertRaises(ValueError):
            MomentumConfig(target_size=1.5)


class TestMomentumStrategy(unittest.TestCase):
    def test_warmup_returns_none(self):
        s = MomentumStrategy(MomentumConfig(lookback=5, threshold=0.0))
        for i in range(1, 6):
            self.assertIsNone(s.generate_signal(i, bar(100 + i, i)))

    def test_uptrend_long(self):
        s = MomentumStrategy(MomentumConfig(lookback=5, threshold=0.0))
        for i in range(1, 7):
            s.generate_signal(i, bar(100 + i, i))
        sig = s.generate_signal(7, bar(106, 7))
        self.assertEqual(sig, 0.2)

    def test_downtrend_short(self):
        s = MomentumStrategy(MomentumConfig(lookback=5, threshold=0.0))
        for i in range(1, 7):
            s.generate_signal(i, bar(200 - i, i))
        sig = s.generate_signal(7, bar(190, 7))
        self.assertEqual(sig, -0.2)

    def test_threshold_deadzone_hold(self):
        s = MomentumStrategy(MomentumConfig(lookback=5, threshold=0.1))
        for i in range(1, 7):
            s.generate_signal(i, bar(100 + i * 0.001, i))
        sig = s.generate_signal(7, bar(100.007, 7))
        self.assertIsNone(sig)

    def test_reset_clears_state(self):
        s = MomentumStrategy(MomentumConfig(lookback=3, threshold=0.0))
        for i in range(1, 5):
            s.generate_signal(i, bar(100 + i, i))
        s.reset()
        self.assertIsNone(s.generate_signal(5, bar(100, 5)))


if __name__ == "__main__":
    unittest.main()
